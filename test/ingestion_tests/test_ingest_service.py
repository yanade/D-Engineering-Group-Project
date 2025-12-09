from src.ingestion.ingest_service import IngestionService

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

    # Fake DB result
    fake_db_instance.fetch_preview.return_value = [
        {"id": 1, "name": "Aaron"},
        {"id": 2, "name": "Yana"}
    ]

    # Fake S3 key
    fake_s3_instance.write_json.return_value = "staff/raw_2025-01-01T12-00-00.json"

    service = IngestionService(bucket="test-bucket")

    
    result = service.ingest_table_preview("staff", limit=2)

    assert result == {
        "table": "staff",
        "rows": 2,
        "s3_key": "staff/raw_2025-01-01T12-00-00.json"
    }

    fake_db_instance.fetch_preview.assert_called_once_with("staff", 2)
    fake_s3_instance.write_json.assert_called_once()



def test_ingest_table_preview_handles_error(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")

    fake_db_instance = mock_db.return_value
    fake_db_instance.fetch_preview.side_effect = Exception("DB failed!")

    service = IngestionService("bucket")

    
    result = service.ingest_table_preview("staff")


    assert result is None



def test_close_calls_db_close(mocker):
    mock_db = mocker.patch("src.ingestion.ingest_service.DatabaseClient")
    mock_s3 = mocker.patch("src.ingestion.ingest_service.S3Client")

    fake_db_instance = mock_db.return_value

    service = IngestionService("bucket")
    service.close()

    fake_db_instance.close.assert_called_once()