import uuid

from app.handlers import _normalized_key_prefix


def test_normalized_key_prefix_preserves_scan_session_layout():
    image_asset_id = uuid.uuid4()
    scan_session_id = uuid.uuid4()

    prefix = _normalized_key_prefix(
        image_asset_id,
        {
            "scan_session_id": scan_session_id,
            "source_type": "SCAN_SESSION",
            "source_id": scan_session_id,
        },
    )

    assert prefix == str(scan_session_id)


def test_normalized_key_prefix_uses_capture_source_when_scan_session_absent():
    image_asset_id = uuid.uuid4()
    capture_session_id = uuid.uuid4()

    prefix = _normalized_key_prefix(
        image_asset_id,
        {
            "scan_session_id": None,
            "source_type": "CAPTURE_SESSION",
            "source_id": capture_session_id,
        },
    )

    assert prefix == f"capture_session/{capture_session_id}"
