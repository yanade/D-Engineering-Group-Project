
# VPC endpoint for S3 ( so lambda can access S3 without internet)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.etl_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  tags = {
    Name  = "${var.project_name}-s3-endpoint"
    Stage = "Week3-Loading"
  }
}
# VPC endpoint for secret manager
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.etl_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  security_group_ids  = [aws_security_group.endpoints_sg.id]
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  private_dns_enabled = true
  tags = {
    Name  = "${var.project_name}-secretsmanager-endpoint"
    Stage = "Week3-Loading"
  }
}
# VPC endpoint for cloudwatch logs
resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = aws_vpc.etl_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  security_group_ids  = [aws_security_group.endpoints_sg.id]
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  private_dns_enabled = true
  tags = {
    Name  = "${var.project_name}-logs-endpoint"
    Stage = "Week3-Loading"
  }
}