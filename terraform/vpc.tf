# vpc.tf - Custom VPC for ETL pipeline
resource "aws_vpc" "etl_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name    = "${var.project_name}-vpc-${var.environment}"
    Project = var.project_name
    Stage   = "ETL-Pipeline"
  }
}

# Public Subnets (for NAT Gateway)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.etl_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-a"
    Type = "Public"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.etl_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-b"
    Type = "Public"
  }
}

# Private Subnets (for Lambda and RDS)
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.etl_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "${var.project_name}-private-a"
    Type = "Private"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.etl_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"
  
  tags = {
    Name = "${var.project_name}-private-b"
    Type = "Private"
  }
}

# Database Subnets (isolated for RDS)
resource "aws_subnet" "db_a" {
  vpc_id            = aws_vpc.etl_vpc.id
  cidr_block        = "10.0.20.0/24"
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "${var.project_name}-db-a"
    Type = "Database"
  }
}

resource "aws_subnet" "db_b" {
  vpc_id            = aws_vpc.etl_vpc.id
  cidr_block        = "10.0.21.0/24"
  availability_zone = "${var.aws_region}b"
  
  tags = {
    Name = "${var.project_name}-db-b"
    Type = "Database"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.etl_vpc.id
  
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# NAT Gateway (for private subnets to access internet)
resource "aws_eip" "nat" {
  domain = "vpc"
  
  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id
  
  tags = {
    Name = "${var.project_name}-nat"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.etl_vpc.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.etl_vpc.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
  
  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# VPC Endpoints (S3, Secrets Manager, CloudWatch)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.etl_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  
  route_table_ids = [aws_route_table.private.id]
  
  tags = {
    Name = "${var.project_name}-s3-endpoint"
  }
}

# Security group for VPC endpoints (Secrets Manager, CloudWatch Logs)
resource "aws_security_group" "vpce_sg" {
  name        = "${var.project_name}-vpce-sg"
  description = "Security group for VPC interface endpoints"
  vpc_id      = aws_vpc.etl_vpc.id

  # Allow HTTPS from Lambda security group
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
    description     = "Allow HTTPS from Lambda"
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-vpce-sg"
  }
}

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.etl_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  security_group_ids = [aws_security_group.vpce_sg.id]
  subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  
  tags = {
    Name = "${var.project_name}-secretsmanager-endpoint"
  }
}

resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = aws_vpc.etl_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  security_group_ids = [aws_security_group.vpce_sg.id]
  subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  
  tags = {
    Name = "${var.project_name}-logs-endpoint"
  }
}

# resource "aws_security_group" "vpce_sg" {
#   name        = "${var.project_name}-vpce-sg"
#   description = "Security group for VPC endpoints"
#   vpc_id      = aws_vpc.etl_vpc.id
  
#   # Allow HTTPS from Lambda security group
#   ingress {
#     from_port       = 443
#     to_port         = 443
#     protocol        = "tcp"
#     security_groups = [aws_security_group.lambda_sg.id]
#     description     = "Allow HTTPS from Lambda"
#   }
  
#   # Allow all outbound
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
  
#   tags = {
#     Name = "${var.project_name}-vpce-sg"
#   }
# }