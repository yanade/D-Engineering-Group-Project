import json
import logging
import os
from ingestion.ingest_service import IngestionService



logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Lambda triggered with event: {event}")
    bucket = os.getenv("LANDING_BUCKET_NAME")
    if not bucket:
        raise ValueError(
            "Environment variable LANDING_BUCKET_NAME is not set.")
    service = IngestionService(bucket=bucket)
    try:
        # table_name = event.get("table", "staff")
        logger.info(f"Starting ingestion for tables in bucket: {bucket}")
        result = service.ingest_all_tables()
        logger.info(f"Ingestion complete: {result}")
        return {"statusCode": 200, "body": json.dumps(
            {"message": "Ingestion Lambda executed", "result": result}), }
    except Exception as e:
        logger.exception("Lambda failed during ingestion")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    finally:
        service.close()
