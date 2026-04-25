import uuid

import pytest
from app import routes
from fastapi import HTTPException


class _Result:
    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _Upload:
    content_type = "image/jpeg"

    async def read(self):
        return b"fake-image-bytes"


class _FakeDb:
    def __init__(self, *, valid_regions=None):
        self.capture_session_id = uuid.uuid4()
        self.protocol_id = uuid.uuid4()
        self.device_id = uuid.uuid4()
        self.valid_regions = valid_regions or ["EXTERIOR_CANVAS"]
        self.statements = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        if "FROM capture_sessions WHERE id" in sql:
            return _Result([{"id": self.capture_session_id, "capture_protocol_id": self.protocol_id, "device_id": self.device_id}])
        if "FROM capture_protocol_regions" in sql:
            return _Result([{"region_code": region} for region in self.valid_regions])
        return _Result()


@pytest.mark.asyncio
async def test_capture_upload_creates_image_asset_and_publishes_canonical_id(monkeypatch):
    db = _FakeDb()
    sent = []

    monkeypatch.setattr(
        routes,
        "validate_image",
        lambda _: {
            "valid": True,
            "file_size_bytes": 16,
            "width": 256,
            "height": 256,
            "image_format": "JPEG",
            "color_mode": "RGB",
            "sha256_checksum": "a" * 64,
        },
    )
    monkeypatch.setattr(routes, "upload_file", lambda *_, **__: "s3://auth-platform-raw-evidence/captures/test.jpg")
    monkeypatch.setattr(routes, "send_message", lambda queue, envelope: sent.append((queue, envelope)))

    async def _audit(*args, **kwargs):
        return None

    monkeypatch.setattr(routes, "record_audit_event", _audit)

    response = await routes.upload_capture_image(
        db.capture_session_id,
        _Upload(),
        region_code="EXTERIOR_CANVAS",
        external_item_id="item_001",
        db=db,
    )

    image_asset_inserts = [params for sql, params in db.statements if "INSERT INTO image_assets" in sql]
    capture_image_inserts = [params for sql, params in db.statements if "INSERT INTO capture_session_images" in sql]

    assert len(image_asset_inserts) == 1
    assert len(capture_image_inserts) == 1
    assert str(image_asset_inserts[0]["id"]) == response["image_asset_id"]
    assert str(capture_image_inserts[0]["image_asset_id"]) == response["image_asset_id"]

    queue, envelope = sent[0]
    assert queue == "image-quality-queue"
    assert str(envelope.image_id) == response["image_asset_id"]
    assert envelope.payload["image_asset_id"] == response["image_asset_id"]
    assert envelope.payload["capture_session_image_id"] == response["id"]


@pytest.mark.asyncio
async def test_capture_upload_rejects_invalid_region_before_creating_assets(monkeypatch):
    db = _FakeDb(valid_regions=["EXTERIOR_CANVAS"])

    monkeypatch.setattr(routes, "send_message", lambda *_: pytest.fail("invalid uploads must not publish events"))

    with pytest.raises(HTTPException) as exc:
        await routes.upload_capture_image(
            db.capture_session_id,
            _Upload(),
            region_code="INVALID_REGION",
            external_item_id="item_001",
            db=db,
        )

    assert exc.value.status_code == 400
    assert not any("INSERT INTO image_assets" in sql for sql, _ in db.statements)
