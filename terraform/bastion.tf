

# 1) Find a recent Amazon Linux AMI (x86_64)
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# 2) SSH key pair from local public key
resource "aws_key_pair" "bastion_key" {
  key_name   = "${var.project_name}-bastion-key-${var.environment}"
  public_key = file("~/.ssh/gamboge_bastion.pub")
}

# 3) Security Group for Bastion (allow SSH only for specific IP)
resource "aws_security_group" "bastion_sg" {
  name        = "${var.project_name}-bastion-sg-${var.environment}"
  description = "Bastion SG: allow SSH from specific IP"
  vpc_id      = aws_vpc.etl_vpc.id

  ingress {
    description = "SSH from specific IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["86.22.195.66/32"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-bastion-sg"
    Project = var.project_name
    Stage   = "Networking"
  }
}

# 4) Bastion EC2 in PUBLIC subnet with public IP
resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public_a.id
  associate_public_ip_address = true

  key_name               = aws_key_pair.bastion_key.key_name
  vpc_security_group_ids = [aws_security_group.bastion_sg.id]

  tags = {
    Name    = "${var.project_name}-bastion-${var.environment}"
    Project = var.project_name
    Stage   = "Networking"
  }
}
