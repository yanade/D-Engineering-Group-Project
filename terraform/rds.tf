# Get existing VPC and subnet information
# data "aws_vpc" "default" {
#     default = true
# }
# data "aws_subnets" "default" {
#     filter {
#         name    = "vpc-id"
#         values  = [data.aws_vpc.default.id]
#     }
# }

# security group for lambda functions
resource "aws_security_group" "lambda_sg" {
  name                   = "${var.project_name}-lambda-sg"
  description            = "Security group for lambda functions in VPC"
  vpc_id                 = aws_vpc.etl_vpc.id
  revoke_rules_on_delete = true

  #     ingress {
  #     description = "Allow HTTPS (443) between Lambdas and Interface VPC Endpoints using the same SG"
  #     from_port   = 443
  #     to_port     = 443
  #     protocol    = "tcp"
  #     self        = true
  #   }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name  = "${var.project_name}-lambda-sg"
    Stage = "Week3-Loading"
  }
}

resource "aws_security_group" "endpoints_sg" {
  name        = "${var.project_name}-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.etl_vpc.id

  # Allow HTTPS (443) traffic from lambda security group
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-endpoints-sg"
  }
}

# security group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS PostgresSQL"
  vpc_id      = aws_vpc.etl_vpc.id
  # Allow PostgresSQL traffic from lambda security group only
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }
  # Allow PostgresSQL traffic from Bastion SG
  ingress {
    description     = "Postgres from Bastion SG"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  # Allow all outbound traffic from RDS (for updates etc..)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name  = "${var.project_name}-rds-sg"
    Stage = "Week3-Loading"
  }
}
# RDS subnet group
resource "aws_db_subnet_group" "warehouse" {
  name       = "${var.project_name}-dw-subnet-group"
  subnet_ids = [aws_subnet.db_a.id, aws_subnet.db_b.id]
  tags = {
    Name  = "Data Warehouse Subnet Group"
    Stage = "Week3-Loading"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "data_warehouse" {
  identifier        = "${var.project_name}-dw-${var.environment}"
  engine            = "postgres"
  engine_version    = var.rds_engine_version
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage

  # Database credentials
  db_name  = "totesys_warehouse"
  username = var.dw_db_username
  password = random_password.dw_password.result

  # VPC Configuration
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.warehouse.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  # Backup and Maintenance
  backup_retention_period = var.rds_backup_retention
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Performance & Security
  storage_encrypted = true
  storage_type      = "gp2"
  multi_az          = false # Change to true for production

  # Database settings
  port = 5432

  # Deletion protection
  deletion_protection = false # Set to true for production
  skip_final_snapshot = true

  tags = {
    Name        = "Totesys Data Warehouse"
    Environment = var.environment
    Project     = var.project_name
  }
}

