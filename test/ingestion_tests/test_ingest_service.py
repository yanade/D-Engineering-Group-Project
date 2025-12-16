from src.ingestion.ingest_service import IngestionService
import os
from datetime import datetime, timezone
import pytest


def test_ingestion_service_initialises(mocker):

    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")

    service = IngestionService(bucket="test-bucket")

    assert service.bucket == "test-bucket"
    mock_db.assert_called_once()
    mock_s3.assert_called_once_with("test-bucket")


def test_ingest_table_preview_success(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_s3_instance = mock_s3.return_value
    # Fake DB result (still valid for refactor)
    fake_db_instance.fetch_preview.return_value = {
        "columns": ["id", "name"],
        "rows": [
            {"id": 1, "name": "Aaron"},
            {"id": 2, "name": "Yana"},
        ],
    }
    # Fake S3 key
    fake_s3_instance.write_json.return_value = "staff/raw_2025-01-01T12-00-00.json"
    service = IngestionService(bucket="test-bucket")
    result = service.ingest_table_preview("staff", limit=2)
    assert result["table"] == "staff"
    assert result["row_count"] == 2
    assert result["s3_key"] == "staff/raw_2025-01-01T12-00-00.json"
    assert "timestamp" in result  # timestamp exists
    fake_db_instance.fetch_preview.assert_called_once_with("staff", 2)
    # IMPORTANT: write_json now receives (table_name, raw_payload)
    fake_s3_instance.write_json.assert_called_once()
    call_args, call_kwargs = fake_s3_instance.write_json.call_args
    assert call_args[0] == "staff"
    raw_payload = call_args[1]
    assert raw_payload["table"] == "staff"
    assert raw_payload["columns"] == ["id", "name"]
    assert raw_payload["rows"] == [
        {"id": 1, "name": "Aaron"},
        {"id": 2, "name": "Yana"},
    ]
    assert raw_payload["limit"] == 2
    assert "timestamp" in raw_payload


def test_ingest_table_preview_handles_error(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_db_instance.fetch_preview.side_effect = Exception("DB failed!")
    service = IngestionService("bucket")
    with pytest.raises(Exception) as exc_info:
        service.ingest_table_preview("staff")
    assert "DB failed!" in str(exc_info.value)


def test_close_calls_db_close(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    service = IngestionService("bucket")
    service.close()
    fake_db_instance.close.assert_called_once()


def test_ingest_table_changes_success_updates_checkpoint(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_s3_instance = mock_s3.return_value
    fake_s3_instance.get_checkpoint.return_value = "2025-01-01T00:00:00+00:00"
    ts1 = datetime(2025, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 1, 3, 11, 0, 0, tzinfo=timezone.utc)
    fake_db_instance.fetch_changes.return_value = [
        {"id": 1, "updated_at": ts1},
        {"id": 2, "updated_at": ts2},
    ]
    fake_db_instance.infer_timestamp_column.return_value = "updated_at"
    fake_s3_instance.write_json.return_value = "staff/changes_2025-01-03.json"
    service = IngestionService(bucket="test-bucket")
    result = service.ingest_table_changes("staff")
    assert result["table"] == "staff"
    assert result["row_count"] == 2
    assert result["s3_key"] == "staff/changes_2025-01-03.json"
    assert result["checkpoint"] == ts2.isoformat()
    fake_s3_instance.get_checkpoint.assert_called_once_with("staff")
    fake_db_instance.fetch_changes.assert_called_once_with("staff", since="2025-01-01T00:00:00+00:00")
    fake_s3_instance.write_json.assert_called_once_with(
        table_name="staff",
        data=fake_db_instance.fetch_changes.return_value,
    )
    fake_db_instance.infer_timestamp_column.assert_called_once_with("staff")
    fake_s3_instance.write_checkpoint.assert_called_once_with("staff", timestamp=ts2)


def test_ingest_table_changes_no_changes_skips_upload(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_s3_instance = mock_s3.return_value
    fake_s3_instance.get_checkpoint.return_value = "2025-01-01T00:00:00+00:00"
    fake_db_instance.fetch_changes.return_value = []
    service = IngestionService(bucket="test-bucket")
    result = service.ingest_table_changes("staff")
    assert result == {
        "table": "staff",
        "row_count": 0,
        "s3_key": None,
        "status": "no_changes",
    }
    fake_db_instance.fetch_changes.assert_called_once_with("staff", since="2025-01-01T00:00:00+00:00")
    fake_s3_instance.write_json.assert_not_called()
    fake_s3_instance.write_checkpoint.assert_not_called()


def test_ingest_table_changes_no_timestamp_column_checkpoint_none(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_s3_instance = mock_s3.return_value
    fake_s3_instance.get_checkpoint.return_value = None
    fake_db_instance.fetch_changes.return_value = [{"id": 1}, {"id": 2}]
    fake_db_instance.infer_timestamp_column.return_value = None
    fake_s3_instance.write_json.return_value = "staff/changes.json"
    service = IngestionService(bucket="test-bucket")
    result = service.ingest_table_changes("staff")
    assert result["table"] == "staff"
    assert result["row_count"] == 2
    assert result["s3_key"] == "staff/changes.json"
    assert result["checkpoint"] is None
    fake_s3_instance.write_checkpoint.assert_not_called()


def test_ingest_table_changes_handles_error(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mocker.patch("src.ingestion.ingest_service.S3Client")
    fake_db_instance = mock_db.return_value
    fake_db_instance.fetch_changes.side_effect = Exception("DB failed!")
    service = IngestionService(bucket="test-bucket")
    with pytest.raises(Exception) as exc_info:
        service.ingest_table_changes("staff")
    assert "DB failed!" in str(exc_info.value)
