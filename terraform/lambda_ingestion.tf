
# Zip up your Python code
data "archive_file" "ingestion_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/../lambda_handler.zip"
  excludes = [
    "**/__pycache__/**",
    "**/*.pyc",
    "test_*.py",
    "**/tests/**",
  ]
}
resource "aws_lambda_function" "ingestion" {

  function_name = "${var.project_name}-ingestion-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = var.lambda_runtime
  handler       = "ingestion.lambda_handler.lambda_handler"

  filename         = data.archive_file.ingestion_lambda.output_path
  source_code_hash = data.archive_file.ingestion_lambda.output_base64sha256



  layers = [aws_lambda_layer_version.dependencies.arn]


  #  vpc_config {
  #   subnet_ids         = [aws_subnet.private_a.id,aws_subnet.private_b.id]
  #   security_group_ids = [aws_security_group.lambda_sg.id]
  # }
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LANDING_BUCKET_NAME = aws_s3_bucket.landing_zone.bucket
      DB_SECRET_ARN       = data.aws_secretsmanager_secret.totesys_creds.arn
      TOTESYS_SECRET_ARN  = data.aws_secretsmanager_secret.totesys_creds.arn
      ENVIRONMENT         = var.environment
      LOG_LEVEL           = "INFO"
    }
  }
  tags = {
    Name    = "${var.project_name}-ingestion-lambda"
    Stage   = "Week1-Ingestion"
    Project = var.project_name
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ingestion_logs" {
  name = "/aws/lambda/${aws_lambda_function.ingestion.function_name}"
  # retention_in_days = 7

  tags = {
    Stage = "Week1-Ingestion"
  }
}
