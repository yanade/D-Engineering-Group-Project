import json
import logging
import os
from contextlib import AbstractContextManager
from typing import Any, List, Optional, Sequence, Tuple, Dict
import boto3
import pg8000.dbapi

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

class WarehouseDBClient(AbstractContextManager):

    # Warehouse Postgres client (Loading Zone).
    # - Uses pg8000.dbapi for standard cursor/commit semantics
    # - Supports efficient cursor.executemany()


    def __init__(self):
        cfg = self._load_dw_config_from_secrets_manager()

        self.host = cfg["host"]
        self.port = int(cfg.get("port", 5432))
        self.database = cfg["database"]

        # Support BOTH key names, because some secrets use "user", some use "username"
        self.user = cfg.get("user") or cfg.get("username")
        self.password = cfg["password"]

        missing = [k for k, v in {
            "host": self.host,
            "database": self.database,
            "user/username": self.user,
            "password": self.password,
        }.items() if not v]
        if missing:
            raise ValueError(f"DW secret is missing required values: {', '.join(missing)}")

        self.conn = None
        logger.info(
            "Initialising WarehouseDBClient host=%s port=%s db=%s user=%s",
            self.host, self.port, self.database, self.user
        )

    def _load_dw_config_from_secrets_manager(self) -> Dict[str, Any]:

        #   Load DW credentials from AWS Secrets Manager.

       
        secret_id = os.getenv("DW_SECRET_ARN")
        if not secret_id:
            raise ValueError("Missing required env var: DW_SECRET_ARN")

        client = boto3.client("secretsmanager")
        resp = client.get_secret_value(SecretId=secret_id)

        # Secrets Manager can store secret as SecretString or SecretBinary.
        if "SecretString" in resp and resp["SecretString"]:
            secret_raw = resp["SecretString"]
        else:
            secret_raw = resp["SecretBinary"].decode("utf-8")

        cfg = json.loads(secret_raw)

        # Fail fast if essential keys are missing
        required_any_user = bool(cfg.get("user") or cfg.get("username"))
        if not cfg.get("host") or not cfg.get("database") or not cfg.get("password") or not required_any_user:
            raise ValueError(
                "DW secret JSON must include: host, database, password, and user or username"
            )

        return cfg    

    def __enter__(self) -> "WarehouseDBClient":
        self.conn = pg8000.dbapi.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        self.conn.autocommit = False
        logger.info("Database connection established")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.conn is None:
            return False
        try:
            if exc_type is None:
                self.conn.commit()
                logger.info("Transaction committed")
            else:
                self.conn.rollback()
                logger.info("Transaction rolled back due to exception: %s", exc_value)
        finally:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.exception("Error closing database connection: %s", e)
            self.conn = None

    def _require_connection(self) -> None:
        if self.conn is None:
            raise RuntimeError("Database connection is not established. Use 'with' context manager.")

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        
        # Execute a single statement.
        # Uses positional params (%s placeholders in SQL).
        self._require_connection()
        logger.debug("Executing SQL: %s", sql)
        cur = self.conn.cursor()
        try:
            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, params)
        finally:
            cur.close()

    def executemany(self, sql: str, param_seq: List[Sequence[Any]], chunk_size: int = 1000) -> None:
        
        # Execute a statement multiple times with different params.
        # Uses positional params (%s placeholders in SQL).
        # Splits param_seq into chunks to avoid very large single executions.

        self._require_connection() 

        if not param_seq:
            logger.info("No parameters provided for executemany; skipping execution.")
            return
        
        logger.info("Executing SQL many times: %s with %s param sets", sql, len(param_seq))
        
        cur = self.conn.cursor()
        try:
            for i in range(0, len(param_seq), chunk_size):
                chunk = param_seq[i:i + chunk_size]
                logger.info("  Executing chunk %s - %s", i, i + len(chunk) - 1)
                cur.executemany(sql, chunk)
        finally:
            cur.close()

    def fetchall(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple]:
        
        # Execute a query and fetch all results.
        # Uses positional params (%s placeholders in SQL).
        self._require_connection()
        logger.info("Fetching all results for SQL: %s with params=%s", sql, params)

        cur = self.conn.cursor()
        try:
            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, params)
            results = cur.fetchall()
            logger.info("Fetched %s rows", len(results))
            return results
        finally:
            cur.close() 