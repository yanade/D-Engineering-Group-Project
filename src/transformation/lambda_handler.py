import os
import json
import logging
import pandas
from transform_service import TransformService


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Transformation Lambda triggered with event={event}")

    landing_bucket = os.getenv("LANDING_BUCKET_NAME")
    processed_bucket = os.getenv("PROCESSED_BUCKET_NAME")

    if not landing_bucket or not processed_bucket:
        raise ValueError("Missing LANDING_BUCKET or PROCESSED_BUCKET env vars")

    try:
        # optional: log key if the event contains it
        record = event.get("Records", [{}])[0]
        raw_key = record.get("s3", {}).get("object", {}).get("key")
        if raw_key:
            logger.info(f"Triggered by new landing object: {raw_key}")

        service = TransformService(ingest_bucket=landing_bucket, processed_bucket=processed_bucket)
        service.run()

        return {"statusCode": 200, "body": json.dumps({"message": "Transformation complete"})}

    except Exception as e:
        logger.exception("Transformation Lambda failed")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
