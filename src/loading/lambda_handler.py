from loading.load_service import LoadService
from loading.db_client import WarehouseDBClient
import json
import logging
import os


# sys.path.append(os.path.join(os.path.dirname(__file__), "..", "vendor"))


logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def lambda_handler(event, context):

    # Loading Lambda entry point.

    # Expected env vars:
    #   - PROCESSED_BUCKET_NAME: S3 bucket with processed parquet outputs

    logger.info("Load Lambda triggered. event=%s", json.dumps(event))

    processed_bucket = _get_env("PROCESSED_BUCKET_NAME")
    checkpoints_prefix = os.getenv(
        "LOAD_CHECKPOINTS_PREFIX",
        "_load_checkpoints")

    try:
        with WarehouseDBClient() as db:
            service = LoadService(
                processed_bucket=processed_bucket,
                db=db,
                checkpoints_prefix=checkpoints_prefix,
            )

            target_table = event.get("table") if isinstance(
                event, dict) else None

            if target_table:
                logger.info("Loading single table=%s", target_table)
                result = service.load_one_table(target_table)
            else:
                logger.info(
                    "Loading all discovered tables from bucket=%s",
                    processed_bucket)
                result = service.load_all_tables()

        return {"statusCode": 200, "body": json.dumps(
            {"message": "Loading complete", "result": result}, default=str), }

    except Exception as e:
        logger.exception("Loading Lambda failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Loading failed", "error": str(e)}),
        }
