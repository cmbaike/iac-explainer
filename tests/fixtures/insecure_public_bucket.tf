provider "aws" {
  region = "us-east-1"
}

# Public website assets — intentionally wide-open for testing
resource "aws_s3_bucket" "public_assets" {
  bucket = "my-public-website-assets"
  acl    = "public-read"

  tags = {
    Purpose = "static-site"
  }
}

# Block public access is explicitly disabled
resource "aws_s3_bucket_public_access_block" "public_assets" {
  bucket = aws_s3_bucket.public_assets.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# No encryption configured at all

# Security group with SSH open to the world
resource "aws_security_group" "open_ssh" {
  name        = "open-ssh-sg"
  description = "Insecure security group — SSH open to internet"
  vpc_id      = "vpc-0abc12345def67890"

  ingress {
    description = "SSH from anywhere — DO NOT USE IN PRODUCTION"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All traffic allowed outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM role with overly permissive policy
resource "aws_iam_role" "admin_role" {
  name = "over-privileged-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "admin_policy" {
  name = "full-admin-policy"
  role = aws_iam_role.admin_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
