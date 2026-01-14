import json
import logging
import os
from loading.load_service import LoadService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Load Lambda triggered with event: {json.dumps(event, default=str)}")
    
    try:
        processed_bucket = os.getenv("PROCESSED_BUCKET_NAME")
        if not processed_bucket:
            raise ValueError("PROCESSED_BUCKET_NAME environment variable is required")
        
        service = LoadService(processed_bucket)
        
        # Check if triggered by S3 event
        if "Records" in event and len(event["Records"]) > 0:
            record = event["Records"][0]
            if "s3" in record:
                s3_key = record["s3"]["object"]["key"]
                result = service.load_from_s3_event(s3_key)
            else:
                # If not S3 event, do full load
                result = service.load_all_tables()
        else:
            # Manual invocation or schedule - do full load
            result = service.load_all_tables()
        
        logger.info(f"Load completed: {result}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Warehouse load successful",
                "result": result
            })
        }
        
    except Exception as e:
        logger.exception("Load Lambda failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    finally:
        if 'service' in locals():
            service.close()