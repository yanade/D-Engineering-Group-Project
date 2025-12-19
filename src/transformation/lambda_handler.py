import os
import json
import logging
# import pandas
from transform_service import TransformService


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Transformation Lambda triggered with event={event}")

    try:

        landing_bucket = os.getenv("LANDING_BUCKET_NAME")
        processed_bucket = os.getenv("PROCESSED_BUCKET_NAME")

        if not landing_bucket or not processed_bucket:
            raise ValueError("Missing LANDING_BUCKET or PROCESSED_BUCKET env vars")
        
        # Extract S3 event info
        records = event.get("Records")
        if not records:
            raise ValueError("No Records found in event")
        
        
        raw_key = records[0].get("s3", {}).get("object", {}).get("key")

        if not raw_key:
            raise ValueError("No S3 object key found in event")

    
        table_name = raw_key.split("/")[0]
        logger.info(f"Detected table '{table_name}' from S3 key '{raw_key}'")

        service = TransformService(
            ingest_bucket=landing_bucket,
            processed_bucket=processed_bucket
        )

        result = service.run_single_table(table_name)

        logger.info(f"Transformation result: {result}")

        return {
            "statusCode": 200, 
            "body": json.dumps(result)}

    except Exception as e:
        logger.exception("Transformation Lambda failed")

        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
