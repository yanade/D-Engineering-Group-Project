

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-role-${var.environment}"
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
    Stage = "Lambda-Execution"
  }

}

# Basic CloudWatch Logs permissions
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for Week 1 (ingestion) and Week 2 (transformation) S3 access
resource "aws_iam_role_policy" "lambda_s3_permissions" {
  name = "${var.project_name}-lambda-s3-permissions"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 permissions Landing zone (read + write for ingestion)
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
    },

    # Processed zone (write for transform)
    {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetObject"
        ]
        Resource = [
          aws_s3_bucket.processed_zone.arn,
          "${aws_s3_bucket.processed_zone.arn}/*"
        ]
      }
    ]
  })
}



# IAM policy attachment for VPC execution
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Update the lambda_secrets_access policy to include DW secret
resource "aws_iam_role_policy" "lambda_secrets_access" {
  name = "${var.project_name}-lambda-secrets-access"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"]
        
        Resource = [
          data.aws_secretsmanager_secret.totesys_creds.arn,
          data.aws_secretsmanager_secret.dw_creds.arn
        ]
      }
    ]
  })
}