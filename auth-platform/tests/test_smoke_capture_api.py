import scripts.smoke_capture_api as smoke_capture_api


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class _Http:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, _url, **_kwargs):
        return self.responses.pop(0)


def test_wait_for_pipeline_handles_quality_dict_response(monkeypatch):
    monkeypatch.setattr(smoke_capture_api, "HTTP", _Http([
        _Response(200, {"quality_status": "PASS"}),
        _Response(200, {"normalized_object_uri": "s3://bucket/key.png"}),
    ]))
    monkeypatch.setattr(smoke_capture_api.time, "sleep", lambda _seconds: None)

    smoke_capture_api.wait_for_pipeline("image-1", max_wait=1)


def test_wait_for_pipeline_handles_legacy_quality_list_response(monkeypatch):
    monkeypatch.setattr(smoke_capture_api, "HTTP", _Http([
        _Response(200, [{"quality_status": "PASS"}]),
        _Response(200, {"normalized_object_uri": "s3://bucket/key.png"}),
    ]))
    monkeypatch.setattr(smoke_capture_api.time, "sleep", lambda _seconds: None)

    smoke_capture_api.wait_for_pipeline("image-1", max_wait=1)


def test_wait_for_pipeline_keeps_polling_after_empty_quality_list(monkeypatch):
    monkeypatch.setattr(smoke_capture_api, "HTTP", _Http([
        _Response(200, []),
        _Response(200, {"quality_status": "PASS"}),
        _Response(200, {"normalized_object_uri": "s3://bucket/key.png"}),
    ]))
    monkeypatch.setattr(smoke_capture_api.time, "sleep", lambda _seconds: None)

    smoke_capture_api.wait_for_pipeline("image-1", max_wait=1)
