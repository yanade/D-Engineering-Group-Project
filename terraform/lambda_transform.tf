

# Package Transform Lambda source code
data "archive_file" "transform_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../src/transformation"
  output_path = "${path.module}/../transform_lambda.zip"

  excludes = [
    "__pycache__",
    "*.pyc",
    "test_*.py",
  ]
}

# resource "aws_lambda_layer_version" "dependencies_trans" {
#   layer_name          = "${var.project_name}-dependencies-transform"
#   filename            = "${path.module}/../transform_deps_layer.zip"
#   compatible_runtimes = ["python3.12"]
#   description         = "Python dependencies for transform lambda"
# }

resource "aws_lambda_function" "transform" {
  function_name = "${var.project_name}-transform-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = var.lambda_runtime

  # this handler in ../src/transformation/lambda_handler.py
  handler = "lambda_handler.lambda_handler"

  filename         = data.archive_file.transform_lambda.output_path
  source_code_hash = data.archive_file.transform_lambda.output_base64sha256

   architectures = ["x86_64"]

  layers = ["arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python311:24"]

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LANDING_BUCKET_NAME   = aws_s3_bucket.landing_zone.bucket
      PROCESSED_BUCKET_NAME = aws_s3_bucket.processed_zone.bucket
      ENVIRONMENT           = var.environment
      LOG_LEVEL             = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-transform-lambda"
    Stage       = "Week2-Transform"
    Project = var.project_name
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "transform_logs" {
  name              = "/aws/lambda/${aws_lambda_function.transform.function_name}"
  retention_in_days = 7

  tags = {
    Stage = "Week2-Transform"
  }
}
