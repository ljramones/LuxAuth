import uuid

import pytest
from app import worker
from auth_common.events import EventEnvelope, EventTypes


class _Db:
    async def commit(self):
        return None

    async def rollback(self):
        return None


class _Factory:
    async def __aenter__(self):
        return _Db()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_worker_accepts_image_asset_id_from_capture_intake_payload(monkeypatch):
    image_asset_id = uuid.uuid4()
    processed = []

    monkeypatch.setattr(worker, "_get_factory", lambda: lambda: _Factory())
    async def _noop(*args, **kwargs):
        return None

    async def _not_idempotent(*args, **kwargs):
        return False

    async def _process(image_id, db):
        processed.append(image_id)

    monkeypatch.setattr(worker, "check_idempotency", _not_idempotent)
    monkeypatch.setattr(worker, "record_processing_start", _noop)
    monkeypatch.setattr(worker, "record_processing_complete", _noop)
    monkeypatch.setattr(worker, "process_image_quality", _process)

    envelope = EventEnvelope(
        event_type=EventTypes.IMAGE_UPLOADED,
        payload={"image_asset_id": str(image_asset_id), "source": "capture_intake"},
    )

    await worker.handle_message(envelope)

    assert processed == [image_asset_id]
