import os
import json
import pytest
from transformation.lambda_handler import lambda_handler
from transformation.transform_service import TransformService


def test_lambda_handler_calls_run(monkeypatch):
    # Import your handler module
    import transformation.lambda_handler as lh

    # Set env vars
    monkeypatch.setenv("LANDING_BUCKET", "landing-bucket")
    monkeypatch.setenv("PROCESSED_BUCKET", "processed-bucket")

    # Fake TransformService that tracks calls
    calls = {"init": None, "run": 0}

    class FakeTransformService:
        def __init__(self, ingest_bucket: str, processed_bucket: str):
            calls["init"] = (ingest_bucket, processed_bucket)

        def run(self):
            calls["run"] += 1

    # Patch TransformService used in the handler module namespace
    monkeypatch.setattr(lh, "TransformService", FakeTransformService)

    # Minimal S3 event (can be any key if you don't guard)
    event = {"Records": [{"s3": {"object": {"key": "ingest/_SUCCESS"}}}]}

    resp = lh.lambda_handler(event, None)

    assert calls["init"] == ("landing-bucket", "processed-bucket")
    assert calls["run"] == 1
    assert resp["statusCode"] == 200
