# S3 Landing Zone bucket
resource "aws_s3_bucket" "landing_zone" {
  bucket = "${var.project_name}-landing-zone" 
  force_destroy = true

  tags = {
    Name = "etl-landing-zone"
  }
}

# Version control stops files being overwritten
resource "aws_s3_bucket_versioning" "landing_zone_versioning" {
  bucket = aws_s3_bucket.landing_zone.id

    versioning_configuration {
    status = "Enabled"
  }
}    
