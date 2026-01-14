import logging
from typing import Dict, Any
from loading.db_client import WarehouseDBClient
from loading.s3_client import S3LoaderClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LoadService:
    """Orchestrates loading data from S3 to RDS warehouse."""
    
    def __init__(self, processed_bucket: str):
        self.s3 = S3LoaderClient(processed_bucket)
        self.db = WarehouseDBClient()
        logger.info(f"LoadService initialized with bucket: {processed_bucket}")
    
    def load_table(self, table_name: str) -> Dict[str, Any]:
        """Load a single table from S3 to RDS."""
        logger.info(f"Loading table: {table_name}")
        
        try:
            # Read data from S3
            df = self.s3.read_latest_parquet(table_name)
            
            # Convert DataFrame to list of dicts
            data = df.to_dict("records")
            
            # Determine if it's a dimension or fact table
            if table_name.startswith("dim_"):
                self.db.upsert_dimension(table_name, data)
                operation = "upsert"
            elif table_name.startswith("fact_"):
                self.db.insert_fact_with_history(table_name, data)
                operation = "insert"
            else:
                raise ValueError(f"Unknown table type: {table_name}")
            
            return {
                "table": table_name,
                "rows_loaded": len(data),
                "operation": operation,
                "status": "success"
            }
            
        except Exception as e:
            logger.exception(f"Failed to load table {table_name}")
            return {
                "table": table_name,
                "error": str(e),
                "status": "failed"
            }
    
    def load_all_tables(self) -> Dict[str, Any]:
        """Load all dimension and fact tables."""
        logger.info("Starting full warehouse load")
        
        # First, ensure tables exist
        self.db.create_tables()
        
        # Define load order (dimensions first, then facts - for foreign keys)
        load_order = [
            "dim_currency",
            "dim_staff", 
            "dim_location",
            "dim_counterparty",
            "dim_design",
            "dim_date",
            "fact_sales_order",
            "fact_purchase_order",
            "fact_payment"
        ]
        
        results = {}
        
        for table in load_order:
            try:
                result = self.load_table(table)
                results[table] = result
            except Exception as e:
                logger.error(f"Failed to load {table}: {e}")
                results[table] = {"table": table, "status": "failed", "error": str(e)}
        
        logger.info("Warehouse load completed")
        return results
    
    def load_from_s3_event(self, s3_key: str) -> Dict[str, Any]:
        """Load based on S3 event (when new Parquet file arrives)."""
        logger.info(f"Processing S3 event for key: {s3_key}")
        
        # Extract table name from S3 key
        # Format: "fact_sales_order/processed_2024-01-01_abc123.parquet"
        table_name = s3_key.split("/")[0]
        
        # Ensure tables exist
        self.db.create_tables()
        
        # Load the specific table
        return self.load_table(table_name)
    
    def close(self):
        """Clean up resources."""
        self.db.close()