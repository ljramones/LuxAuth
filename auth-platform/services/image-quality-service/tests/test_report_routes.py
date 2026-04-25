import uuid
from datetime import UTC, datetime

import pytest
from app import routes
from app.main import app
from httpx import ASGITransport, AsyncClient


class _Mappings:
    def __init__(self, row):
        self.row = row

    def one_or_none(self):
        return self.row


class _Result:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return _Mappings(self.row)


class _Db:
    def __init__(self, row):
        self.row = row

    async def execute(self, *_args, **_kwargs):
        return _Result(self.row)


@pytest.mark.asyncio
async def test_get_report_returns_single_report_object():
    image_asset_id = uuid.uuid4()
    row = {
        "image_asset_id": image_asset_id,
        "sharpness_score": 0.91,
        "exposure_score": 0.82,
        "glare_score": 0.03,
        "quality_status": "PASS",
        "issues": [],
        "created_at": datetime.now(UTC),
    }

    async def override_db():
        yield _Db(row)

    app.dependency_overrides[routes.get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/reports/{image_asset_id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert body["image_asset_id"] == str(image_asset_id)
    assert body["quality_status"] == "PASS"


@pytest.mark.asyncio
async def test_get_report_returns_404_when_report_missing():
    image_asset_id = uuid.uuid4()

    async def override_db():
        yield _Db(None)

    app.dependency_overrides[routes.get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/reports/{image_asset_id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert resp.json() == {"detail": "report not found"}
