provider "aws" {
  region = "eu-west-1"
}

# Web server security group — allows HTTP/HTTPS from the internet, SSH from a specific IP
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for the web server"
  vpc_id      = "vpc-0abc12345def67890"

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from office IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["203.0.113.10/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = "production"
  }
}

# t3.small web server running Amazon Linux 2
resource "aws_instance" "web" {
  ami                    = "ami-0d71ea30463e0ff49"
  instance_type          = "t3.small"
  subnet_id              = "subnet-0abc12345def67890"
  vpc_security_group_ids = [aws_security_group.web.id]
  key_name               = "my-key-pair"

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name        = "web-server"
    Environment = "production"
  }
}

# Elastic IP so the web server has a stable public address
resource "aws_eip" "web" {
  instance = aws_instance.web.id
  domain   = "vpc"
}
