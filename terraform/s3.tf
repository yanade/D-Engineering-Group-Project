# Random suffix for unique bucket names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# LANDING ZONE BUCKET ONLY (Week 1)
resource "aws_s3_bucket" "landing_zone" {
  bucket = "gamboge-landing-${var.environment}-${random_id.bucket_suffix.hex}"
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