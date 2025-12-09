resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "etl_ingestion" {
  function_name = "${var.project_name}-ingestion-lambda"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "etl_handler.handler"
 

  # Use the ZIP that archive_file just built 
  filename         = data.archive_file.etl_lambda.output_path
  source_code_hash = data.archive_file.etl_lambda.output_base64sha256

  timeout     = 60
  memory_size = 256

  environment {
    variables = {
      STAGE               = "dev"
      LANDING_BUCKET_NAME = aws_s3_bucket.landing_zone.bucket
    }
  }

  tags = {
    Name    = "${var.project_name}-ingestion-lambda"
    Project = var.project_name
  }
}




# S3 LANDING ZONE PERMISSION POLICY 

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.landing_zone.arn,
          "${aws_s3_bucket.landing_zone.arn}/*"
        ]
      }
    ]
  })
}

