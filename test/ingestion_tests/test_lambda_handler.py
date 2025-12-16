import json
import os
from src.ingestion.lambda_handler import lambda_handler
from src.ingestion.ingest_service import IngestionService


def test_lambda_handler(mocker):

    mocker.patch("os.getenv", return_value="test_bucket")

    mock_service = mocker.patch("src.ingestion.lambda_handler.IngestionService")

    fake_service = mock_service.return_value
    fake_service.ingest_all_tables.return_value = {
        "tables_processed": 1,
        "status": "ok",
    }
    resp = lambda_handler({}, None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["result"]["status"] == "ok"
    fake_service.ingest_all_tables.assert_called_once()
    fake_service.close.assert_called_once()

    # result = mock_service.return_value.ingest_all_tables()

    # response = lambda_handler()
    # body = json.loads(response["body"])

    # assert response["statusCode"] == 200
