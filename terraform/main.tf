terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "econet-chatbot-terraform-state"  # Replace with your S3 bucket name
    key            = "terraform.tfstate"         # The path within the bucket to store the state
    region         = "us-east-1"               # The AWS region of the bucket
        
  }
}

provider "aws" {
  region     = "us-east-1"
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}
  
# Define variables for AWS credentials and other configurations
variable "aws_access_key" {
  description = "AWS Access Key"
  type        = string
  sensitive   = true
}
variable "aws_secret_key" {
  description = "AWS Secret Key"
  type        = string
  sensitive   = true
}
variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
}

resource "tls_private_key" "rsa_4096" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.rsa_4096.public_key_openssh
}

resource "local_file" "private_key" {
  content  = tls_private_key.rsa_4096.private_key_pem
  filename = var.key_name
}

resource "aws_security_group" "sg_ec2" {
  name        = "sg_ec2_airflow"
  description = "Security group for EC2 running Airflow and related services"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "airflow_instance" {
  ami           = "ami-0866a3c8686eaeeba"
  instance_type = "t2.xlarge"  # Increased instance size due to resource requirements
  key_name      = aws_key_pair.key_pair.key_name
  vpc_security_group_ids = [aws_security_group.sg_ec2.id]
  
  tags = {
    Name = "airflow_instance"
  }
  
  root_block_device {
    volume_size = 60
    volume_type = "gp2"
  }
  
  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y docker.io docker-compose
              sudo systemctl start docker
              sudo systemctl enable docker
              sudo usermod -aG docker ubuntu
              EOF
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.airflow_instance.public_ip
}
