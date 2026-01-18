import pandas as pd
import pytest

# Update this import to your real module path
from loading.load_service import LoadService


@pytest.fixture
def fake_df():
    return pd.DataFrame([{"id": 1, "name": "Aaron"}, {"id": 2, "name": "Musab"}])


@pytest.fixture
def service(mocker):
    """
    Create LoadService but replace its dependencies (S3LoaderClient, WarehouseDBClient).
    """
  
    mock_s3_cls = mocker.patch("loading.load_service.S3LoaderClient")
    mock_db_cls = mocker.patch("loading.load_service.WarehouseDBClient")

    s3 = mock_s3_cls.return_value
    db = mock_db_cls.return_value

    svc = LoadService(processed_bucket="processed-bucket")
    return svc, s3, db


def test_init_creates_clients(service):
    svc, s3, db = service
    assert svc.s3 is s3
    assert svc.db is db


def test_load_table_dim_calls_upsert(service, fake_df):
    svc, s3, db = service
    s3.read_latest_parquet.return_value = fake_df

    result = svc.load_table("dim_staff")

    db.upsert_dimension.assert_called_once()
    db.insert_fact_with_history.assert_not_called()

    args, _ = db.upsert_dimension.call_args
    assert args[0] == "dim_staff"
    assert args[1] == fake_df.to_dict("records")

    assert result["table"] == "dim_staff"
    assert result["rows_loaded"] == 2
    assert result["operation"] == "upsert"
    assert result["status"] == "success"


def test_load_table_fact_calls_insert(service, fake_df):
    svc, s3, db = service
    s3.read_latest_parquet.return_value = fake_df

    result = svc.load_table("fact_sales_order")

    db.insert_fact_with_history.assert_called_once()
    db.upsert_dimension.assert_not_called()

    args, _ = db.insert_fact_with_history.call_args
    assert args[0] == "fact_sales_order"
    assert args[1] == fake_df.to_dict("records")

    assert result["table"] == "fact_sales_order"
    assert result["rows_loaded"] == 2
    assert result["operation"] == "insert"
    assert result["status"] == "success"


def test_load_table_unknown_prefix_returns_failed(service, fake_df):
    svc, s3, db = service
    s3.read_latest_parquet.return_value = fake_df

    result = svc.load_table("weird_table")

    db.upsert_dimension.assert_not_called()
    db.insert_fact_with_history.assert_not_called()

    assert result["table"] == "weird_table"
    assert result["status"] == "failed"
    assert "Unknown table type" in result["error"]


def test_load_table_s3_read_failure_returns_failed(service):
    svc, s3, db = service
    s3.read_latest_parquet.side_effect = Exception("s3 broken")

    result = svc.load_table("dim_currency")

    db.upsert_dimension.assert_not_called()
    assert result["table"] == "dim_currency"
    assert result["status"] == "failed"
    assert "s3 broken" in result["error"]


def test_load_table_db_failure_returns_failed(service, fake_df):
    svc, s3, db = service
    s3.read_latest_parquet.return_value = fake_df
    db.upsert_dimension.side_effect = Exception("db broken")

    result = svc.load_table("dim_currency")

    db.upsert_dimension.assert_called_once()
    assert result["table"] == "dim_currency"
    assert result["status"] == "failed"
    assert "db broken" in result["error"]


def test_load_all_tables_calls_create_tables_once_and_loads_in_order(service, mocker):
    svc, s3, db = service

    # Spy on load_table so we can verify order without re-testing load_table itself
    load_table_spy = mocker.patch.object(svc, "load_table", side_effect=lambda t: {"table": t, "status": "success"})

    results = svc.load_all_tables()

    db.create_tables.assert_called_once()

    expected_order = [
        "dim_currency",
        "dim_staff",
        "dim_location",
        "dim_counterparty",
        "dim_design",
        "dim_date",
        "fact_sales_order",
        "fact_purchase_order",
        "fact_payment",
    ]

    assert [call.args[0] for call in load_table_spy.call_args_list] == expected_order
    assert set(results.keys()) == set(expected_order)
    assert results["dim_currency"]["status"] == "success"


def test_load_all_tables_handles_exception_and_continues(service, mocker):
    svc, s3, db = service

    def side_effect(table):
        if table == "dim_location":
            raise Exception("boom")
        return {"table": table, "status": "success"}

    mocker.patch.object(svc, "load_table", side_effect=side_effect)

    results = svc.load_all_tables()

    db.create_tables.assert_called_once()

    assert results["dim_location"]["status"] == "failed"
    assert "boom" in results["dim_location"]["error"]
   
    assert results["fact_payment"]["status"] == "success"


def test_load_from_s3_event_extracts_table_and_creates_tables_then_loads(service, mocker):
    svc, s3, db = service
    load_table_spy = mocker.patch.object(svc, "load_table", return_value={"status": "success"})

    result = svc.load_from_s3_event("fact_sales_order/processed_2026-01-01_abc.parquet")

    db.create_tables.assert_called_once()
    load_table_spy.assert_called_once_with("fact_sales_order")
    assert result["status"] == "success"


def test_close_calls_db_close(service):
    svc, s3, db = service
    svc.close()
    db.close.assert_called_once()