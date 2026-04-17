# ─────────────────────────────────────────────────────────────────────────────
# outputs.tf
# ─────────────────────────────────────────────────────────────────────────────

output "api_gateway_url" {
  description = "Base URL for the Game Store API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cloudfront_url" {
  description = "Frontend URL (use this to access the app)"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_s3_bucket" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.frontend.bucket
}

/*output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.game_store.id
}*/

/*output "cognito_client_id" {
  description = "Cognito App Client ID (used in frontend config)"
  value       = aws_cognito_user_pool_client.frontend_updated.id
}*/

output "lambda_function_arns" {
  description = "ARNs of all deployed Lambda functions"
  value       = { for k, fn in aws_lambda_function.functions : k => fn.arn }
}

output "dynamodb_table_arns" {
  description = "ARNs of all DynamoDB tables"
  value       = { for k, tbl in aws_dynamodb_table.tables : k => tbl.arn }
}

output "cart_api_url" {
  description = "Full URL for the Cart Lambda endpoint (used by Order service)"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/cart"
}