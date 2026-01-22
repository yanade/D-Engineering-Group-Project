terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket  = "gamboge-state-bucket"
    key     = "terraform/week1-ingestion.tfstate"
    region  = "eu-west-2"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      ProjectName  = "ETL Pipeline - Gamboge"
      DeployedFrom = "Terraform"
      Stage        = "Week1-Ingestion"
      Environment  = "dev"
    }
  }
}