import json
import logging
import os
import urllib.parse

import boto3


logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    Transform Lambda entry point.
    Triggered by S3 ObjectCreated events from the landing zone.
    """

    logger.info("Transform Lambda triggered")
    logger.debug("Received event: %s", json.dumps(event))

    try:
        # 1. Extract S3 info from event
        record = event["Records"][0]
        source_bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]

        # S3 keys are URL-encoded
        source_key = urllib.parse.unquote_plus(raw_key)

        logger.info("Processing object from bucket=%s, key=%s", source_bucket, source_key)

        # 2. Read environment variables
        processed_bucket = os.environ["PROCESSED_BUCKET_NAME"]

        # 3. Placeholder for transform logic
        # (we will implement this in the next step)
        logger.info("Transform target bucket=%s (logic not implemented yet)", processed_bucket)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Transform Lambda executed successfully",
                    "source_bucket": source_bucket,
                    "source_key": source_key,
                    "processed_bucket": processed_bucket,
                }
            ),
        }

    except Exception as exc:
        logger.exception("Transform Lambda failed")
        raise exc
