import json
import uuid

import pytest
from auth_common.idempotency import record_processing_failed


class _Result:
    def mappings(self):
        return self

    def first(self):
        return {
            "stage": "IMAGE_QUALITY",
            "scan_session_id": None,
            "image_id": self.image_id,
        }

    def __init__(self, image_id):
        self.image_id = image_id


class _Db:
    def __init__(self, image_id):
        self.image_id = image_id
        self.statements = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        if "SELECT stage, scan_session_id, image_id" in sql:
            return _Result(self.image_id)
        return _Result(self.image_id)


@pytest.mark.asyncio
async def test_record_processing_failed_writes_processing_failed_audit_event():
    image_id = uuid.uuid4()
    event_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    db = _Db(str(image_id))

    await record_processing_failed(
        db,
        "image|IMAGE_QUALITY|v1",
        "boom",
        correlation_id=correlation_id,
        stage="IMAGE_QUALITY",
        source_service="image-quality-service",
        event_id=event_id,
    )

    audit_inserts = [params for sql, params in db.statements if "INSERT INTO audit_events" in sql]
    assert len(audit_inserts) == 1
    assert audit_inserts[0]["event_type"] == "processing.failed"
    assert audit_inserts[0]["correlation_id"] == str(correlation_id)
    assert audit_inserts[0]["image_id"] == str(image_id)
    payload = json.loads(audit_inserts[0]["payload"])
    assert payload["stage"] == "IMAGE_QUALITY"
    assert payload["source_service"] == "image-quality-service"
    assert payload["error_message"] == "boom"
    assert payload["event_id"] == str(event_id)
