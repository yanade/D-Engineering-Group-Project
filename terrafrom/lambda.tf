data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir  = "${path.module}/../src/ingestion"
  output_path = "${path.module}/../lambda_handler.zip"
  excludes = [
    "__pycache__",
    "*.pyc",
    "test_*.py",  # Exclude test files if any
  ]
}
resource "aws_lambda_function" "etl_ingestion" {
  depends_on = [aws_lambda_layer_version.dependencies]
  function_name = "${var.project_name}-ingestion-lambda"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  # Handler stays the same
  handler       = "lambda_handler.lambda_handler"
  # UPDATE filename path:
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  layers = [
    aws_lambda_layer_version.dependencies.arn
  ]
  timeout     = 60
  memory_size = 256
  environment {
    variables = {
      LANDING_BUCKET_NAME = aws_s3_bucket.landing_zone.bucket
      DB_SECRET_ARN       = data.aws_secretsmanager_secret.db_creds.arn
    }
  }
  tags = {
    Name    = "${var.project_name}-ingestion-lambda"
    Project = var.project_name
  }
}