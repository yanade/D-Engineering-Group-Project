# import json
# import os
# import pytest


# from loading.lambda_handler import lambda_handler


# def test_lambda_handler_full_load_when_no_records(mocker):
#     # env
#     mocker.patch.dict(os.environ, {"PROCESSED_BUCKET_NAME": "processed"}, clear=True)

#     # mock service + its methods
#     mock_service = mocker.Mock()
#     mock_service.load_all_tables.return_value = {"dim_currency": {"status": "success"}}
#     mocker.patch("loading.lambda_handler.LoadService", return_value=mock_service)

#     event = {}  # no Records => full load
#     resp = lambda_handler(event, context=None)

#     assert resp["statusCode"] == 200
#     body = json.loads(resp["body"])
#     assert body["message"] == "Warehouse load successful"
#     assert body["result"] == {"dim_currency": {"status": "success"}}

#     mock_service.load_all_tables.assert_called_once()
#     mock_service.load_from_s3_event.assert_not_called()
#     mock_service.close.assert_called_once()


# def test_lambda_handler_full_load_when_record_not_s3(mocker):
#     mocker.patch.dict(os.environ, {"PROCESSED_BUCKET_NAME": "processed"}, clear=True)

#     mock_service = mocker.Mock()
#     mock_service.load_all_tables.return_value = {"ok": True}
#     mocker.patch("loading.lambda_handler.LoadService", return_value=mock_service)

#     event = {"Records": [{"eventSource": "aws:sns"}]}  # record present but no "s3"
#     resp = lambda_handler(event, context=None)

#     assert resp["statusCode"] == 200
#     body = json.loads(resp["body"])
#     assert body["result"] == {"ok": True}

#     mock_service.load_all_tables.assert_called_once()
#     mock_service.load_from_s3_event.assert_not_called()
#     mock_service.close.assert_called_once()


# def test_lambda_handler_s3_event_calls_load_from_s3_event(mocker):
#     mocker.patch.dict(os.environ, {"PROCESSED_BUCKET_NAME": "processed"}, clear=True)

#     mock_service = mocker.Mock()
#     mock_service.load_from_s3_event.return_value = {"table": "fact_sales_order", "status": "success"}
#     mocker.patch("loading.lambda_handler.LoadService", return_value=mock_service)

#     event = {
#         "Records": [
#             {
#                 "s3": {
#                     "object": {
#                         "key": "fact_sales_order/processed_2026-01-01_abc.parquet"
#                     }
#                 }
#             }
#         ]
#     }

#     resp = lambda_handler(event, context=None)

#     assert resp["statusCode"] == 200
#     body = json.loads(resp["body"])
#     assert body["result"]["status"] == "success"

#     mock_service.load_from_s3_event.assert_called_once_with(
#         "fact_sales_order/processed_2026-01-01_abc.parquet"
#     )
#     mock_service.load_all_tables.assert_not_called()
#     mock_service.close.assert_called_once()


# def test_lambda_handler_missing_env_returns_500_and_does_not_instantiate_service(mocker):
#     mocker.patch.dict(os.environ, {}, clear=True)

#     load_service_patch = mocker.patch("loading.lambda_handler.LoadService")

#     resp = lambda_handler({}, context=None)

#     assert resp["statusCode"] == 500
#     body = json.loads(resp["body"])
#     assert "PROCESSED_BUCKET_NAME environment variable is required" in body["error"]

#     load_service_patch.assert_not_called()


# def test_lambda_handler_when_service_raises_returns_500_and_closes(mocker):
#     mocker.patch.dict(os.environ, {"PROCESSED_BUCKET_NAME": "processed"}, clear=True)

#     mock_service = mocker.Mock()
#     mock_service.load_all_tables.side_effect = Exception("boom")
#     mocker.patch("loading.lambda_handler.LoadService", return_value=mock_service)

#     resp = lambda_handler({}, context=None)

#     assert resp["statusCode"] == 500
#     body = json.loads(resp["body"])
#     assert "boom" in body["error"]

#     mock_service.close.assert_called_once()