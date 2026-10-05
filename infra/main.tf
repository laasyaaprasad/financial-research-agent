# One small EC2 instance running the chat UI in Docker behind Caddy (HTTPS). Deployment is pull-based: GitHub Actions
# pushes the image to ghcr.io (private), and the instance checks for a new one every 2 minutes, logging in with a
# read-only package token, so GitHub needs no AWS access (the AWS organization's policy doesn't allow GitHub OIDC).
# No SSH (SSM Session Manager instead); secrets stay in SSM Parameter Store (uploaded by deploy/put_secrets.py), never
# in this state. Every resource is named after var.name, so this sits beside other deployments in the account.
#
#   terraform -chdir=infra init && terraform -chdir=infra apply
#   terraform -chdir=infra destroy        (removes everything; delete the SSM parameters separately)

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

variable "region" { # the AWS organization's policy allows only this region
  type    = string
  default = "us-east-2"
}
variable "name" {
  type    = string
  default = "fin-research-agent"
}
variable "github_repo" {
  type    = string
  default = "laasyaaprasad/financial-research-agent"
}
variable "instance_type" { # free-tier eligible
  type    = string
  default = "t3.micro"
}

provider "aws" {
  region = var.region
  default_tags { tags = { app = var.name } }
}

data "aws_caller_identity" "me" {}
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  param_path = "/${var.name}"
  image      = "ghcr.io/${lower(var.github_repo)}"
  domain     = "${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io" # a hostname for the IP, so Caddy can get a cert
}

# ---------- the instance ----------

resource "aws_iam_role" "instance" {
  name = "${var.name}-instance"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" }
  }] })
}

resource "aws_iam_role_policy_attachment" "ssm_core" { # SSM agent: Run Command and Session Manager instead of SSH
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "read_secrets" {
  role = aws_iam_role.instance.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect   = "Allow", Action = ["ssm:GetParametersByPath", "ssm:GetParameters"]
    Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter${local.param_path}*"
  }] })
}

resource "aws_iam_instance_profile" "instance" {
  name = "${var.name}-instance"
  role = aws_iam_role.instance.name
}

resource "aws_security_group" "web" {
  name        = "${var.name}-web"
  description = "HTTP and HTTPS in; everything out"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
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

resource "aws_eip" "app" {
  domain = "vpc"
}

resource "aws_instance" "app" {
  ami                    = nonsensitive(data.aws_ssm_parameter.al2023.value)
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.instance.name
  vpc_security_group_ids = [aws_security_group.web.id]
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }
  user_data = templatefile("${path.module}/user_data.sh", {
    caddyfile = file("${path.module}/../deploy/Caddyfile")
    deploy_sh = templatefile("${path.module}/../deploy/deploy.sh", {
      region     = var.region, image = local.image, domain = local.domain,
      param_path = local.param_path, registry_user = split("/", var.github_repo)[0]
    })
  })
  user_data_replace_on_change = true
  lifecycle { ignore_changes = [ami] } # a newer AMI shouldn't replace the running instance
  tags = { Name = var.name }
}

resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}

# ---------- outputs ----------

output "url" { value = "https://${local.domain}" }
output "instance_id" { value = aws_instance.app.id }
output "image" { value = local.image }
