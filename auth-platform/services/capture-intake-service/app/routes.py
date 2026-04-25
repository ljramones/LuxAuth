import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.database import get_db
from auth_common.events import EventEnvelope, EventTypes
from auth_common.imaging import validate_image
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.s3 import upload_file

logger = get_logger(settings.service_name)
router = APIRouter()


# ── Health ──────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}

@router.get("/ready")
async def ready():
    return {"status": "ready"}


# ── Capture Protocols ───────────────────────────────────────────────
@router.get("/capture-protocols")
async def list_protocols(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM capture_protocols WHERE status = 'active' ORDER BY protocol_code"))
    return [dict(r) for r in result.mappings()]

@router.get("/capture-protocols/{protocol_code}")
async def get_protocol(protocol_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM capture_protocols WHERE protocol_code = :code"),
        {"code": protocol_code},
    )
    protocol = result.mappings().first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")

    regions = await db.execute(
        text("SELECT * FROM capture_protocol_regions WHERE capture_protocol_id = :pid ORDER BY sort_order"),
        {"pid": str(protocol["id"])},
    )
    return {**dict(protocol), "regions": [dict(r) for r in regions.mappings()]}


class CreateProtocol(BaseModel):
    protocol_code: str
    protocol_version: str = "v0.1.0"
    brand: str | None = None
    category: str | None = None
    material: str | None = None
    description: str | None = None
    regions: list[dict] = []


@router.post("/capture-protocols", status_code=201)
async def create_protocol(body: CreateProtocol, db: AsyncSession = Depends(get_db)):
    pid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text("""INSERT INTO capture_protocols (id, protocol_code, protocol_version, brand, category, material, description, created_at, updated_at)
                VALUES (:id, :code, :version, :brand, :cat, :mat, :desc, :now, :now)"""),
        {"id": pid, "code": body.protocol_code, "version": body.protocol_version,
         "brand": body.brand, "cat": body.category, "mat": body.material,
         "desc": body.description, "now": now},
    )
    for i, region in enumerate(body.regions):
        await db.execute(
            text("""INSERT INTO capture_protocol_regions (id, capture_protocol_id, region_code, display_name, min_images, sort_order)
                    VALUES (:id, :pid, :code, :name, :min, :sort)"""),
            {"id": uuid.uuid4(), "pid": pid, "code": region["region_code"],
             "name": region.get("display_name", region["region_code"]),
             "min": region.get("min_images", 1), "sort": i},
        )
    await record_audit_event(db, "CAPTURE_PROTOCOL_CREATED", payload={"protocol_code": body.protocol_code})
    return {"id": str(pid), "protocol_code": body.protocol_code}


# ── Capture Sessions ────────────────────────────────────────────────
class CreateCaptureSession(BaseModel):
    device_id: str
    calibration_id: str | None = None
    capture_protocol_code: str
    source_type: str = "api"
    operator: str | None = None
    notes: str | None = None


@router.post("/capture-sessions", status_code=201)
async def create_capture_session(body: CreateCaptureSession, db: AsyncSession = Depends(get_db)):
    # Validate protocol
    proto = await db.execute(
        text("SELECT id FROM capture_protocols WHERE protocol_code = :code AND status = 'active'"),
        {"code": body.capture_protocol_code},
    )
    proto_row = proto.first()
    if not proto_row:
        raise HTTPException(status_code=400, detail=f"Protocol not found: {body.capture_protocol_code}")

    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text("""INSERT INTO capture_sessions (id, device_id, calibration_id, capture_protocol_id,
                source_type, operator, status, notes, created_at, updated_at)
                VALUES (:id, :did, :cid, :pid, :src, :op, 'CREATED', :notes, :now, :now)"""),
        {"id": sid, "did": body.device_id, "cid": body.calibration_id,
         "pid": proto_row[0], "src": body.source_type, "op": body.operator,
         "notes": body.notes, "now": now},
    )
    await record_audit_event(db, "CAPTURE_SESSION_CREATED",
                             payload={"capture_session_id": str(sid), "protocol": body.capture_protocol_code})
    return {"id": str(sid), "status": "CREATED", "capture_protocol_code": body.capture_protocol_code}


@router.get("/capture-sessions/{capture_session_id}")
async def get_capture_session(capture_session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM capture_sessions WHERE id = :id"), {"id": str(capture_session_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Capture session not found")
    return dict(row)


@router.get("/capture-sessions/{capture_session_id}/status")
async def get_capture_session_status(capture_session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Get session + protocol
    session = await db.execute(
        text("SELECT cs.*, cp.protocol_code FROM capture_sessions cs JOIN capture_protocols cp ON cp.id = cs.capture_protocol_id WHERE cs.id = :id"),
        {"id": str(capture_session_id)},
    )
    row = session.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get required regions
    required = await db.execute(
        text("SELECT region_code, min_images FROM capture_protocol_regions WHERE capture_protocol_id = :pid ORDER BY sort_order"),
        {"pid": str(row["capture_protocol_id"])},
    )
    required_regions = {r["region_code"]: r["min_images"] for r in required.mappings()}

    # Get uploaded images per region
    uploaded = await db.execute(
        text("SELECT region_code, count(*) as cnt FROM capture_session_images WHERE capture_session_id = :sid GROUP BY region_code"),
        {"sid": str(capture_session_id)},
    )
    uploaded_counts = {r["region_code"]: r["cnt"] for r in uploaded.mappings()}

    region_status = []
    all_satisfied = True
    for rc, min_img in required_regions.items():
        count = uploaded_counts.get(rc, 0)
        satisfied = count >= min_img
        if not satisfied:
            all_satisfied = False
        region_status.append({"region_code": rc, "required": min_img, "uploaded": count, "satisfied": satisfied})

    missing = [rs["region_code"] for rs in region_status if not rs["satisfied"]]

    return {
        "capture_session_id": str(capture_session_id),
        "status": row["status"],
        "protocol_code": row["protocol_code"],
        "all_regions_satisfied": all_satisfied,
        "total_images": sum(uploaded_counts.values()),
        "missing_regions": missing,
        "region_status": region_status,
    }


# ── Image Upload ────────────────────────────────────────────────────
@router.post("/capture-sessions/{capture_session_id}/images", status_code=201)
async def upload_capture_image(
    capture_session_id: uuid.UUID,
    file: UploadFile,
    region_code: str = Form(...),
    external_item_id: str = Form(default="default_item"),
    capture_index: int = Form(default=0),
    magnification_profile: str = Form(default=None),
    lighting_profile: str = Form(default=None),
    authenticity_status: str = Form(default=None),
    label_confidence: str = Form(default=None),
    provenance_type: str = Form(default=None),
    notes: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    # Validate session
    session = await db.execute(
        text("SELECT id, capture_protocol_id, device_id FROM capture_sessions WHERE id = :id"),
        {"id": str(capture_session_id)},
    )
    sess = session.mappings().first()
    if not sess:
        raise HTTPException(status_code=404, detail="Capture session not found")

    # Validate region code against protocol
    valid = await db.execute(
        text("SELECT region_code FROM capture_protocol_regions WHERE capture_protocol_id = :pid"),
        {"pid": str(sess["capture_protocol_id"])},
    )
    valid_regions = [r["region_code"] for r in valid.mappings()]
    if region_code not in valid_regions:
        raise HTTPException(status_code=400, detail=f"Invalid region '{region_code}'. Valid: {valid_regions}")

    # Read and validate image
    content = await file.read()
    validation = validate_image(content)
    if not validation.get("valid", False):
        raise HTTPException(status_code=400, detail={"error": "Invalid image", "issues": validation.get("issues", [])})

    image_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    ext = (validation.get("image_format") or "bin").lower()
    if ext == "jpeg":
        ext = "jpg"

    # Upload to S3
    s3_key = f"captures/{capture_session_id}/items/{external_item_id}/raw/{image_id}.{ext}"
    raw_uri = upload_file(settings.raw_evidence_bucket, s3_key, content,
                          content_type=file.content_type or "application/octet-stream")

    # Store metadata
    await db.execute(
        text("""INSERT INTO capture_session_images
                (id, capture_session_id, external_item_id, region_code, capture_index,
                 device_id, raw_object_uri, file_size_bytes, content_type,
                 width, height, image_format, sha256_checksum,
                 magnification_profile, lighting_profile, calibration_profile,
                 authenticity_status, label_confidence, provenance_type, notes, created_at)
                VALUES (:id, :sid, :eid, :rc, :ci,
                        :did, :uri, :size, :ct,
                        :w, :h, :fmt, :sha,
                        :mag, :light, :cal,
                        :auth, :lconf, :prov, :notes, :now)"""),
        {
            "id": image_id, "sid": capture_session_id, "eid": external_item_id,
            "rc": region_code, "ci": capture_index,
            "did": sess["device_id"], "uri": raw_uri,
            "size": validation.get("file_size_bytes"), "ct": file.content_type,
            "w": validation.get("width"), "h": validation.get("height"),
            "fmt": validation.get("image_format"), "sha": validation.get("sha256_checksum"),
            "mag": magnification_profile, "light": lighting_profile, "cal": None,
            "auth": authenticity_status, "lconf": label_confidence,
            "prov": provenance_type, "notes": notes, "now": now,
        },
    )

    # Update session status to CAPTURING
    await db.execute(
        text("UPDATE capture_sessions SET status = 'CAPTURING', updated_at = :now WHERE id = :id AND status = 'CREATED'"),
        {"id": str(capture_session_id), "now": now},
    )

    # Publish to image quality queue
    envelope = EventEnvelope(
        event_type=EventTypes.IMAGE_UPLOADED,
        correlation_id=get_correlation_id(),
        image_id=image_id,
        source_service=settings.service_name,
        payload={
            "capture_session_id": str(capture_session_id),
            "region_code": region_code,
            "raw_object_uri": raw_uri,
            "external_item_id": external_item_id,
            "source": "capture_intake",
        },
    )
    try:
        send_message(settings.image_quality_queue, envelope)
    except Exception:
        logger.warning("queue_publish_failed", image_id=str(image_id))

    await record_audit_event(
        db, "CAPTURE_SESSION_IMAGE_UPLOADED",
        image_id=image_id,
        payload={"capture_session_id": str(capture_session_id), "region_code": region_code},
    )

    return {
        "id": str(image_id),
        "capture_session_id": str(capture_session_id),
        "region_code": region_code,
        "raw_object_uri": raw_uri,
        "width": validation.get("width"),
        "height": validation.get("height"),
        "sha256_checksum": validation.get("sha256_checksum"),
    }


# ── Complete Session ────────────────────────────────────────────────
@router.post("/capture-sessions/{capture_session_id}/complete")
async def complete_capture_session(capture_session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Get status info
    status_resp = await get_capture_session_status(capture_session_id, db)

    if status_resp["all_regions_satisfied"]:
        new_status = "COMPLETE"
        event = "CAPTURE_SESSION_COMPLETED"
    else:
        new_status = "INCOMPLETE"
        event = "CAPTURE_SESSION_INCOMPLETE"

    now = datetime.now(timezone.utc)
    await db.execute(
        text("UPDATE capture_sessions SET status = :status, updated_at = :now WHERE id = :id"),
        {"status": new_status, "id": str(capture_session_id), "now": now},
    )

    await record_audit_event(
        db, event,
        payload={
            "capture_session_id": str(capture_session_id),
            "status": new_status,
            "missing_regions": status_resp["missing_regions"],
        },
    )

    return {
        "capture_session_id": str(capture_session_id),
        "status": new_status,
        "all_regions_satisfied": status_resp["all_regions_satisfied"],
        "total_images": status_resp["total_images"],
        "missing_regions": status_resp["missing_regions"],
        "region_status": status_resp["region_status"],
    }
