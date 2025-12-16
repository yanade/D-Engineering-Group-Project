import os
import pytest
from unittest.mock import MagicMock
from src.ingestion.db_client import DatabaseClient


def test_db_client_initialises_correctly(mocker):
    # Fake environment variables
    mock_env = {
        "DB_HOST": "localhost",
        "DB_NAME": "testdb",
        "DB_USER": "user",
        "DB_PASSWORD": "pass",
        "DB_PORT": "5432",
    }
    mocker.patch.dict(os.environ, mock_env)

    # Mock the Connection object ***in the db_client module***
    fake_connection = mocker.Mock()
    mocker.patch("src.ingestion.db_client.Connection", return_value=fake_connection)

    client = DatabaseClient()

    assert client.host == "localhost"
    assert client.database == "testdb"
    assert client.user == "user"
    assert client.port == 5432
    assert client.conn == fake_connection


def test_missing_env_variables_raises_error(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)

    with pytest.raises(ValueError):
        DatabaseClient()


def test_run_executes_sql_and_returns_dict_rows(mocker):
    # Arrange environment
    mocker.patch.dict(
        os.environ,
        {
            "DB_HOST": "localhost",
            "DB_NAME": "testdb",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_PORT": "5432",
        },
    )

    # Fake row + columns returned by database
    fake_conn = mocker.Mock()
    fake_conn.run.return_value = [(1, "Aaron")]
    fake_conn.columns = [{"name": "id"}, {"name": "name"}]

    mocker.patch("src.ingestion.db_client.Connection", return_value=fake_conn)

    client = DatabaseClient()

    result = client.run("SELECT * FROM test")

    assert result == [{"id": 1, "name": "Aaron"}]
    fake_conn.run.assert_called_once()


def test_fetch_preview_calls_run_with_limit(mocker):
    mocker.patch.dict(
        os.environ,
        {
            "DB_HOST": "localhost",
            "DB_NAME": "testdb",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_PORT": "5432",
        },
    )

    fake_conn = mocker.Mock()
    fake_conn.run.return_value = []
    fake_conn.columns = []

    mocker.patch("src.ingestion.db_client.Connection", return_value=fake_conn)

    client = DatabaseClient()

    mocker.patch.object(client, "run", return_value=[{"id": 1}])

    result = client.fetch_preview("staff", limit=5)

    client.run.assert_called_with("SELECT * FROM staff LIMIT :limit", {"limit": 5})

    assert isinstance(result, dict)


def test_close_calls_connection_close(mocker):
    mocker.patch.dict(
        os.environ,
        {
            "DB_HOST": "localhost",
            "DB_NAME": "testdb",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_PORT": "5432",
        },
    )

    fake_conn = mocker.Mock()
    mocker.patch("src.ingestion.db_client.Connection", return_value=fake_conn)

    client = DatabaseClient()
    client.close()

    fake_conn.close.assert_called_once()
