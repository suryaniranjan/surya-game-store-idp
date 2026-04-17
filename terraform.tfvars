aws_region     = "ap-southeast-1"
aws_profile    = "AWS-Academy-Developer-726101441380"
project_name   = "game-store"
s3_bucket_name = "surya-games-store-images"

common_tags = {
  Project     = "GameStore"
  ManagedBy   = "Terraform"
  Environment = "dev"
}

# ─────────────────────────────────────────
# ADD THESE TO YOUR EXISTING terraform.tfvars
# ─────────────────────────────────────────
environment  = "dev"

#Replace with your actual Cart API Gateway URL after running terraform output
cart_api_url = "https://h4b0tuf5u4.execute-api.ap-southeast-1.amazonaws.com/cart"