# rds.tf - Updated for custom VPC

# Security group for Lambda functions
resource "aws_security_group" "lambda_sg" {
  name        = "${var.project_name}-lambda-sg-${var.environment}"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.etl_vpc.id
  
  # Allow outbound to RDS
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Allow within VPC
  }
  
  # Allow outbound HTTPS for AWS services
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Allow outbound for VPC endpoints
  # egress {
  #   from_port   = 0
  #   to_port     = 0
  #   protocol    = "-1"
  #   cidr_blocks = ["10.0.0.0/16"]
  # }
  # egress {
  #   from_port   = 53
  #   to_port     = 53
  #   protocol    = "udp"
  #   cidr_blocks = ["10.0.0.0/16"]
  #   description = "Allow DNS resolution"
  # }
  
  tags = {
    Name  = "${var.project_name}-lambda-sg"
    Stage = "ETL-Pipeline"
  }
}

# Security group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg-${var.environment}"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.etl_vpc.id
  
  # Allow PostgreSQL from Lambda security group
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["80.7.249.208/32"]  # YOUR IP ONLY
    # Get your IP: curl ifconfig.me
  }
  
  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name  = "${var.project_name}-rds-sg"
    Stage = "ETL-Pipeline"
  }
}

# RDS subnet group (using database subnets)
resource "aws_db_subnet_group" "warehouse" {
  name       = "${var.project_name}-dw-subnet-group-${var.environment}"
  subnet_ids = [aws_subnet.db_a.id, aws_subnet.db_b.id]
  
  tags = {
    Name  = "Data Warehouse Subnet Group"
    Stage = "ETL-Pipeline"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "data_warehouse" {
  identifier         = "${var.project_name}-dw-${var.environment}"
  engine             = "postgres"
  engine_version     = var.rds_engine_version
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  
  # Database credentials
  db_name  = "totesys_warehouse"
  username = var.dw_db_username
  password = var.dw_db_password
  
  # VPC Configuration
  db_subnet_group_name   = aws_db_subnet_group.warehouse.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = true  # CRITICAL: Set to false
  
  # Backup and Maintenance
  backup_retention_period = var.rds_backup_retention
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  
  # Performance & Security
  storage_encrypted      = true
  storage_type          = "gp2"
  multi_az             = false  # Change to true for production
  
  # Database settings
  port = 5432
  
  # Deletion protection
  deletion_protection = false  # Set to true for production
  skip_final_snapshot = true
  
  tags = {
    Name        = "Totesys Data Warehouse"
    Environment = var.environment
    Project     = var.project_name
  }
}

# # Store RDS credentials in Secrets Manager
# resource "aws_secretsmanager_secret" "dw_creds_2" {
#   name        = "${var.project_name}/dw/${var.environment}-warehouse"
#   description = "Data warehouse RDS credentials"
  
#   tags = {
#     Stage       = "ETL-Pipeline"
#     Environment = var.environment
#     Database    = "warehouse"
#   }
# }
# EXISTING warehouse secret (already in AWS)

# resource "aws_secretsmanager_secret" "dw_creds" {
#   name = "${var.project_name}/dw/${var.environment}"

#   recovery_window_in_days = 0  # allow immediate recreate if needed

#   tags = {
#     Stage       = "ETL-Pipeline"
#     Environment = var.environment
#     Database    = "warehouse"
#   }
# }
data "aws_secretsmanager_secret" "dw_creds" {
  name = "${var.project_name}/dw/${var.environment}"
}

resource "aws_secretsmanager_secret_version" "dw_creds_value" {
  secret_id = data.aws_secretsmanager_secret.dw_creds.id

  secret_string = jsonencode({
    host     = aws_db_instance.data_warehouse.address
    port     = aws_db_instance.data_warehouse.port
    database = aws_db_instance.data_warehouse.db_name
    username = var.dw_db_username
    password = var.dw_db_password
  })
}
