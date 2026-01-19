import json
import os
import pytest



# IMPORTANT: update this import to your real module path
from loading.db_client import WarehouseDBClient


@pytest.fixture
def mock_secret_payload():
    return {
        "host": "dw-host",
        "port": 5432,
        "database": "dw",
        "username": "dw_user",
        "password": "dw_pass",
    }


@pytest.fixture
def patched_env(mocker):
    mocker.patch.dict(os.environ, {"DW_SECRET_ARN": "arn:aws:secretsmanager:eu-west-2:123:secret:dw"})


def test_client_initialises_correctly(mocker, patched_env, mock_secret_payload):
    # Patch secrets manager client
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    # Patch pg8000 connection
    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()

    # asserts: secrets manager called correctly
    fake_sm_client.get_secret_value.assert_called_once_with(
        SecretId=os.environ["DW_SECRET_ARN"]
    )

    # asserts: pg8000 connection called with secret values
    loading_conn = __import__("loading.db_client", fromlist=["pg8000"]).pg8000.native.Connection
    loading_conn.assert_called_once_with(
        host="dw-host",
        port=5432,
        database="dw",
        user="dw_user",
        password="dw_pass",
        timeout=10,
    )

    assert client.conn == fake_conn


def test_missing_dw_secret_arn_raises_value_error(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)
    with pytest.raises(ValueError, match="DW_SECRET_ARN environment variable is required"):
        WarehouseDBClient()


def test_create_tables_executes_all_create_statements(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()
    client.create_tables()

    # There are multiple CREATE TABLE statements; ensure we executed "a bunch" and they look right.
    assert fake_conn.run.call_count >= 8  # dims + facts in your list

    # Spot-check: first call includes CREATE TABLE IF NOT EXISTS dim_currency
    first_sql = fake_conn.run.call_args_list[0][0][0]
    assert "CREATE TABLE IF NOT EXISTS dim_currency" in first_sql

    # Spot-check: includes a fact table
    all_sql = " ".join(call.args[0] for call in fake_conn.run.call_args_list)
    assert "CREATE TABLE IF NOT EXISTS fact_sales_order" in all_sql
    assert "CREATE TABLE IF NOT EXISTS fact_purchase_order" in all_sql
    assert "CREATE TABLE IF NOT EXISTS fact_payment" in all_sql


def test_upsert_dimension_no_data_does_nothing(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()
    client.upsert_dimension("dim_currency", data=[])

    fake_conn.run.assert_not_called()


def test_upsert_dimension_builds_sql_and_calls_run_for_each_row(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()

    rows = [
        {"currency_id": 1, "currency_code": "GBP"},
        {"currency_id": 2, "currency_code": "USD"},
    ]

    client.upsert_dimension("dim_currency", rows)

    # called once per row
    assert fake_conn.run.call_count == 2

    # validate SQL shape from first call
    sql_used = fake_conn.run.call_args_list[0].args[0]
    assert "INSERT INTO dim_currency (currency_id, currency_code)" in sql_used
    assert "ON CONFLICT (currency_id)" in sql_used
    assert "DO UPDATE SET currency_code = EXCLUDED.currency_code" in sql_used

    # validate params were passed (matches your current implementation: **params)
    _, kwargs_0 = fake_conn.run.call_args_list[0]
    assert kwargs_0 == {"currency_id": 1, "currency_code": "GBP"}

    _, kwargs_1 = fake_conn.run.call_args_list[1]
    assert kwargs_1 == {"currency_id": 2, "currency_code": "USD"}


def test_upsert_dimension_rolls_back_and_raises_on_error(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()

    # First insert raises; rollback should be attempted
    fake_conn.run.side_effect = Exception("boom")
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()

    with pytest.raises(Exception, match="boom"):
        client.upsert_dimension("dim_currency", [{"currency_id": 1, "currency_code": "GBP"}])

    # Ensure rollback attempted
    fake_conn.run.assert_any_call("ROLLBACK")


def test_insert_fact_with_history_no_data_does_nothing(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()
    client.insert_fact_with_history("fact_sales_order", data=[])

    fake_conn.run.assert_not_called()


def test_insert_fact_with_history_calls_run_for_each_row(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()

    rows = [
        {
            "sales_order_id": 10,
            "created_date": "2026-01-01",
            "created_time": "10:00:00",
            "last_updated_date": "2026-01-01",
            "last_updated_time": "10:00:00",
            "units_sold": 3,
        },
        {
            "sales_order_id": 11,
            "created_date": "2026-01-02",
            "created_time": "11:00:00",
            "last_updated_date": "2026-01-02",
            "last_updated_time": "11:00:00",
            "units_sold": 5,
        },
    ]

    client.insert_fact_with_history("fact_sales_order", rows)

    assert fake_conn.run.call_count == 2

    sql_used = fake_conn.run.call_args_list[0].args[0]
    assert "INSERT INTO fact_sales_order" in sql_used
    assert "sales_order_id" in sql_used

    _, kwargs_0 = fake_conn.run.call_args_list[0]
    assert kwargs_0["sales_order_id"] == 10

    _, kwargs_1 = fake_conn.run.call_args_list[1]
    assert kwargs_1["sales_order_id"] == 11


def test_insert_fact_with_history_rolls_back_and_raises_on_error(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    fake_conn.run.side_effect = Exception("insert failed")
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()

    with pytest.raises(Exception, match="insert failed"):
        client.insert_fact_with_history(
            "fact_sales_order",
            [{
                "sales_order_id": 10,
                "created_date": "2026-01-01",
                "created_time": "10:00:00",
                "last_updated_date": "2026-01-01",
                "last_updated_time": "10:00:00",
                "units_sold": 3,
            }],
        )

    fake_conn.run.assert_any_call("ROLLBACK")


def test_close_calls_connection_close(mocker, patched_env, mock_secret_payload):
    fake_sm_client = mocker.Mock()
    fake_sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret_payload)
    }
    mocker.patch("loading.db_client.boto3.client", return_value=fake_sm_client)

    fake_conn = mocker.Mock()
    mocker.patch("loading.db_client.pg8000.native.Connection", return_value=fake_conn)

    client = WarehouseDBClient()
    client.close()

    fake_conn.close.assert_called_once()