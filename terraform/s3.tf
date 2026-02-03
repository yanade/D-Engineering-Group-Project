# Random suffix for unique bucket names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# LANDING ZONE BUCKET ONLY (Week 1)
resource "aws_s3_bucket" "landing_zone" {
  bucket        = "gamboge-landing-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "landing-zone"
    Environment = var.environment
    Stage       = "Week1-Ingestion"
  }
}

# Versioning for immutability
resource "aws_s3_bucket_versioning" "landing_zone" {
  bucket = aws_s3_bucket.landing_zone.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "landing_zone" {
  bucket = aws_s3_bucket.landing_zone.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
# Block public access
resource "aws_s3_bucket_public_access_block" "landing_zone" {
  bucket = aws_s3_bucket.landing_zone.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


#--------------------------------
# PROCESSED ZONE BUCKET 
#--------------------------------

resource "random_id" "processed_bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "processed_zone" {
  bucket        = "${var.project_name}-processed-${var.environment}-${random_id.processed_bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "processed-zone"
    Environment = var.environment
    Stage       = "Week2-Transformation"
  }
}

resource "aws_s3_bucket_versioning" "processed_zone" {
  bucket = aws_s3_bucket.processed_zone.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_zone" {
  bucket = aws_s3_bucket.processed_zone.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "processed_zone" {
  bucket                  = aws_s3_bucket.processed_zone.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Dead Letter Queues for Lambda functions

resource "aws_sqs_queue" "ingestion_dlq" {
  name                      = "${var.project_name}-ingestion-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days
  tags = {
    Name    = "${var.project_name}-ingestion-dlq"
    Stage   = "DLQ"
    Project = var.project_name
  }
}

resource "aws_sqs_queue" "transform_dlq" {
  name                      = "${var.project_name}-transform-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days
  tags = {
    Name    = "${var.project_name}-transform-dlq"
    Stage   = "DLQ"
    Project = var.project_name
  }
}

resource "aws_sqs_queue" "loading_dlq" {
  name                      = "${var.project_name}-loading-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days
  tags = {
    Name    = "${var.project_name}-loading-dlq"
    Stage   = "DLQ"
    Project = var.project_name
  }
}
