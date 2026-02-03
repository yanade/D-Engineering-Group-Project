

resource "aws_iam_role" "ingestion_lambda_role" {
  name = "${var.project_name}-ingestion-lambda-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Role = "IngestionLambda"
    Stage = "Ingestion"
  }
}

resource "aws_iam_role" "transform_lambda_role" {
  name = "${var.project_name}-transform-lambda-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Role = "TransformLambda"
    Stage = "Transform"
  }
}

resource "aws_iam_role" "loading_lambda_role" {
  name = "${var.project_name}-loading-lambda-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Role = "LoadingLambda"
    Stage = "Loading"
  }
}

# Basic CloudWatch Logs permissions for all roles

resource "aws_iam_role_policy_attachment" "ingestion_basic_execution" {
  role       = aws_iam_role.ingestion_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "transform_basic_execution" {
  role       = aws_iam_role.transform_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "loading_basic_execution" {
  role       = aws_iam_role.loading_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}



resource "aws_iam_role_policy_attachment" "ingestion_lambda_vpc_access" {
  role       = aws_iam_role.ingestion_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "loading_lambda_vpc_access" {
  role       = aws_iam_role.loading_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

## IAM policy per Role for S3 access

# Ingestion Lambda S3 permissions

resource "aws_iam_role_policy" "ingestion_lambda_s3_permissions" {
  name = "${var.project_name}-ingestion-lambda-s3-permissions"
  role = aws_iam_role.ingestion_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.landing_zone.arn}/*"
        ]
      },
      {
        Effect    = "Allow"
        Action    = "secretsmanager:GetSecretValue"
        Resource  = data.aws_secretsmanager_secret.totesys_creds.arn
      },
      {
        Effect     = "Allow"
        Action     = "sqs:SendMessage"
        Resource   = aws_sqs_queue.ingestion_dlq.arn
      }
    ]
  })
}

# Transformation Lambda S3 permissions

resource "aws_iam_role_policy" "transform_lambda_s3_permissions" {
  name = "${var.project_name}-transform-lambda-s3-permissions"
  role = aws_iam_role.transform_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.landing_zone.arn
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.landing_zone.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.processed_zone.arn}/*"
      },
      {
        Effect     = "Allow"
        Action     = "sqs:SendMessage"
        Resource   = aws_sqs_queue.transform_dlq.arn
      }
    ]
  })
}


# Loading Lambda S3 permissions

resource "aws_iam_role_policy" "loading_lambda_s3_permissions" {
  name = "${var.project_name}-loading-lambda-s3-permissions"
  role = aws_iam_role.loading_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.processed_zone.arn
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.processed_zone.arn}/*"
      },
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.dw_creds.arn
      },
      {
        Effect     = "Allow"
        Action     = "sqs:SendMessage"
        Resource   = aws_sqs_queue.loading_dlq.arn
      }
    ]
  })
}
