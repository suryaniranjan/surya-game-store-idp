# ─────────────────────────────────────────────────────────────────────────────
# outputs.tf
# ─────────────────────────────────────────────────────────────────────────────
#
# CHANGES FROM ORIGINAL:
#   Added outputs at the bottom of the file under "CloudWatch Observability":
#     - cloudwatch_dashboard_url
#     - cloudwatch_alarm_arns
#     - lambda_log_group_names
#     - api_gateway_log_group_name
#   All original outputs are completely unchanged.
# ─────────────────────────────────────────────────────────────────────────────

# ── Original outputs (unchanged) ─────────────────────────────────────────────

output "api_gateway_url" {
  description = "Base URL for the Game Store API"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}v1"
}

output "cloudfront_url" {
  description = "Frontend URL (use this to access the app)"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_s3_bucket" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.frontend.bucket
}

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
  value       = "${aws_apigatewayv2_stage.default.invoke_url}v1/cart"
}

# ── CloudWatch Observability outputs (new) ────────────────────────────────────

output "cloudwatch_dashboard_url" {
  description = "Direct URL to the game-store-observability CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=game-store-observability"
}

output "lambda_log_group_names" {
  description = "CloudWatch Log Group names for all Lambda functions (14-day retention)"
  value       = { for k, lg in aws_cloudwatch_log_group.lambda_logs : k => lg.name }
}

output "api_gateway_log_group_name" {
  description = "CloudWatch Log Group name for API Gateway access logs"
  value       = aws_cloudwatch_log_group.api_gw_access_logs.name
}

output "cloudwatch_alarm_arns" {
  description = "ARNs of all CloudWatch alarms created for the game store"
  value = merge(
    {
      payment_errors    = aws_cloudwatch_metric_alarm.payment_errors.arn
      api_latency       = aws_cloudwatch_metric_alarm.api_latency.arn
      all_lambda_errors = aws_cloudwatch_metric_alarm.all_lambda_errors.arn
    },
    {
      for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_throttles :
      "dynamodb_throttle_${k}" => alarm.arn
    }
  )
}
