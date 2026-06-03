variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use for authentication"
  type        = string
  default     = "AWS-Academy-Developer-726101441380"
}

variable "project_name" {
  description = "Prefix applied to every resource name"
  type        = string
  default     = "game-store"
}

variable "s3_bucket_name" {
  description = "S3 bucket used for product images (must already exist or be created separately)"
  type        = string
  default     = "surya-games-store-images"
}

variable "common_tags" {
  description = "Tags applied to every resource"
  type        = map(string)
  default = {
    Project     = "GameStore"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}

# ─────────────────────────────────────────
# ADD THESE TO YOUR EXISTING variables.tf
# ─────────────────────────────────────────

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
 type        = string
  default     = "dev"
}

variable "cart_api_url" {
  description = "Base URL of the Cart Lambda API Gateway endpoint"
  type        = string
  # Example: "https://abc123.execute-api.us-east-1.amazonaws.com/dev/cart"
}