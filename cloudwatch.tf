# ─────────────────────────────────────────────────────────────────────────────
# cloudwatch.tf  —  GameStore Observability
#
# What this file manages:
#   1. CloudWatch Log Groups          — one per Lambda, with 14-day retention
#   2. IAM additions                  — PutMetricData + enhanced log permissions
#   3. API Gateway access log group   — for HTTP API v2 access logs
#   4. CloudWatch Dashboard           — game-store-observability
#   5. CloudWatch Alarms              — Payment errors, API latency,
#                                       Lambda errors, DynamoDB throttles
#   6. CloudFront monitoring sub      — enhanced metrics (Cache Hit Ratio etc.)
#
# Depends on: main.tf, frontend.tf
# Region note: CloudFront metrics always live in us-east-1. The dashboard
#              widget for CloudFront uses an explicit region override.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 1. CLOUDWATCH LOG GROUPS — one per Lambda function
#    Without these, Lambda auto-creates log groups with no retention.
#    We create them explicitly so Terraform controls retention and lifecycle.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = local.lambdas

  # Lambda always writes to /aws/lambda/<function_name>
  name              = "/aws/lambda/${var.project_name}-${each.key}"
  retention_in_days = 14

  tags = merge(var.common_tags, {
    Name    = "/aws/lambda/${var.project_name}-${each.key}"
    Service = each.key
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. API GATEWAY ACCESS LOG GROUP
#    HTTP API v2 access logs require a dedicated log group.
#    The ARN of this group is referenced in main.tf's stage resource.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "api_gw_access_logs" {
  name              = "/aws/apigateway/${var.project_name}-api/access-logs"
  retention_in_days = 14

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-api-access-logs"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. IAM — allow API Gateway to push logs to CloudWatch
#    HTTP API v2 requires an account-level CloudWatch role to be set.
#    This is a one-time account setting — safe to apply multiple times.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "api_gw_cloudwatch" {
  name = "${var.project_name}-apigw-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "apigateway.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "api_gw_cloudwatch_logs" {
  role       = aws_iam_role.api_gw_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Sets the account-level API Gateway CloudWatch role
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gw_cloudwatch.arn
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. IAM — allow Lambda execution role to publish custom metrics
#    The existing AWSLambdaBasicExecutionRole already covers logs:PutLogEvents.
#    This inline policy adds cloudwatch:PutMetricData for future custom metrics.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_iam_role_policy" "lambda_cloudwatch_metrics" {
  name = "${var.project_name}-lambda-cloudwatch-metrics-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudwatch:PutMetricData"]
      Resource = "*"
    }]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. CLOUDFRONT ENHANCED METRICS SUBSCRIPTION
#    Enables: CacheHitRate, OriginLatency, RequestsHttpsPercentage etc.
#    Billed at ~$10/month per distribution.
#    Standard free metrics (Requests, ErrorRate, BytesDownloaded) are
#    always available without this subscription.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_cloudfront_monitoring_subscription" "frontend" {
  distribution_id = aws_cloudfront_distribution.frontend.id

  monitoring_subscription {
    realtime_metrics_subscription_config {
      realtime_metrics_subscription_status = "Enabled"
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# 6. CLOUDWATCH DASHBOARD — game-store-observability
#
# Layout (each row = 24 units wide):
#   Row 1 — Lambda: Invocations, Errors, Duration, Throttles  (4 widgets)
#   Row 2 — API Gateway: Requests, Latency, 4XX, 5XX          (4 widgets)
#   Row 3 — DynamoDB: Read/Write Capacity, Throttles          (3 widgets)
#   Row 4 — CloudFront: Requests, Bandwidth, ErrorRate,
#            CacheHitRate                                      (4 widgets)
#
# CloudFront note: all CF metrics must specify region="us-east-1" in the
# widget definition regardless of your deployment region.
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_dashboard" "game_store" {
  dashboard_name = "game-store-observability"

  dashboard_body = jsonencode({
    widgets = [

      # ── ROW 1 HEADER ────────────────────────────────────────────────────────
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "## 🚀 Lambda Metrics — All Functions"
        }
      },

      # ── LAMBDA: Invocations (all 6 functions on one graph) ──────────────────
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 6
        height = 6
        properties = {
          title  = "Lambda Invocations"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [
            for k in keys(local.lambdas) :
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-${k}"]
          ]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── LAMBDA: Errors ───────────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 6
        y      = 1
        width  = 6
        height = 6
        properties = {
          title  = "Lambda Errors"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [
            for k in keys(local.lambdas) :
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-${k}"]
          ]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── LAMBDA: Duration (p99) ───────────────────────────────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 1
        width  = 6
        height = 6
        properties = {
          title  = "Lambda Duration p99 (ms)"
          view   = "timeSeries"
          stat   = "p99"
          period = 300
          region = var.aws_region
          metrics = [
            for k in keys(local.lambdas) :
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-${k}"]
          ]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── LAMBDA: Throttles ────────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 18
        y      = 1
        width  = 6
        height = 6
        properties = {
          title  = "Lambda Throttles"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [
            for k in keys(local.lambdas) :
            ["AWS/Lambda", "Throttles", "FunctionName", "${var.project_name}-${k}"]
          ]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── ROW 2 HEADER ────────────────────────────────────────────────────────
      {
        type   = "text"
        x      = 0
        y      = 7
        width  = 24
        height = 1
        properties = {
          markdown = "## 🌐 API Gateway Metrics"
        }
      },

      # ── API GW: Request Count ────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 6
        height = 6
        properties = {
          title  = "API Gateway — Request Count"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [[
            "AWS/ApiGateway", "Count",
            "ApiId", aws_apigatewayv2_api.game_store.id,
            "Stage", "$default"
          ]]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── API GW: Latency (p99) ────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 6
        y      = 8
        width  = 6
        height = 6
        properties = {
          title  = "API Gateway — Latency p99 (ms)"
          view   = "timeSeries"
          stat   = "p99"
          period = 300
          region = var.aws_region
          metrics = [[
            "AWS/ApiGateway", "Latency",
            "ApiId", aws_apigatewayv2_api.game_store.id,
            "Stage", "$default"
          ]]
          annotations = {
            horizontal = [{
              label = "Alarm threshold"
              value = 2000
              color = "#ff6961"
            }]
          }
          yAxis = { left = { min = 0 } }
        }
      },

      # ── API GW: 4XX Errors ───────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 6
        height = 6
        properties = {
          title  = "API Gateway — 4XX Errors"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [[
            "AWS/ApiGateway", "4XXError",
            "ApiId", aws_apigatewayv2_api.game_store.id,
            "Stage", "$default"
          ]]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── API GW: 5XX Errors ───────────────────────────────────────────────────
      {
        type   = "metric"
        x      = 18
        y      = 8
        width  = 6
        height = 6
        properties = {
          title  = "API Gateway — 5XX Errors"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = [[
            "AWS/ApiGateway", "5XXError",
            "ApiId", aws_apigatewayv2_api.game_store.id,
            "Stage", "$default"
          ]]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── ROW 3 HEADER ────────────────────────────────────────────────────────
      {
        type   = "text"
        x      = 0
        y      = 14
        width  = 24
        height = 1
        properties = {
          markdown = "## 🗄️ DynamoDB Metrics — All Tables"
        }
      },

      # ── DYNAMODB: Consumed Read Capacity ────────────────────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 15
        width  = 8
        height = 6
        properties = {
          title  = "DynamoDB — Consumed Read Capacity"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = concat(
            [
              for k, tbl in local.dynamodb_tables :
              ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", tbl.name]
            ],
            [["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "game-orders"]]
          )
          yAxis = { left = { min = 0 } }
        }
      },

      # ── DYNAMODB: Consumed Write Capacity ───────────────────────────────────
      {
        type   = "metric"
        x      = 8
        y      = 15
        width  = 8
        height = 6
        properties = {
          title  = "DynamoDB — Consumed Write Capacity"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = concat(
            [
              for k, tbl in local.dynamodb_tables :
              ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", tbl.name]
            ],
            [["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "game-orders"]]
          )
          yAxis = { left = { min = 0 } }
        }
      },

      # ── DYNAMODB: Throttled Requests ────────────────────────────────────────
      {
        type   = "metric"
        x      = 16
        y      = 15
        width  = 8
        height = 6
        properties = {
          title  = "DynamoDB — Throttled Requests"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = var.aws_region
          metrics = concat(
            [
              for k, tbl in local.dynamodb_tables :
              ["AWS/DynamoDB", "ThrottledRequests", "TableName", tbl.name]
            ],
            [["AWS/DynamoDB", "ThrottledRequests", "TableName", "game-orders"]]
          )
          annotations = {
            horizontal = [{
              label = "Alarm threshold"
              value = 1
              color = "#ff6961"
            }]
          }
          yAxis = { left = { min = 0 } }
        }
      },

      # ── ROW 4 HEADER ────────────────────────────────────────────────────────
      {
        type   = "text"
        x      = 0
        y      = 21
        width  = 24
        height = 1
        properties = {
          markdown = "## ☁️ CloudFront Metrics"
        }
      },

      # ── CLOUDFRONT: Requests ─────────────────────────────────────────────────
      # CloudFront metrics are ALWAYS in us-east-1 regardless of deployment region
      {
        type   = "metric"
        x      = 0
        y      = 22
        width  = 6
        height = 6
        properties = {
          title  = "CloudFront — Requests"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = "us-east-1"
          metrics = [[
            "AWS/CloudFront", "Requests",
            "DistributionId", aws_cloudfront_distribution.frontend.id,
            "Region", "Global"
          ]]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── CLOUDFRONT: Bandwidth (BytesDownloaded) ──────────────────────────────
      {
        type   = "metric"
        x      = 6
        y      = 22
        width  = 6
        height = 6
        properties = {
          title  = "CloudFront — Bandwidth (Bytes Downloaded)"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          region = "us-east-1"
          metrics = [[
            "AWS/CloudFront", "BytesDownloaded",
            "DistributionId", aws_cloudfront_distribution.frontend.id,
            "Region", "Global"
          ]]
          yAxis = { left = { min = 0 } }
        }
      },

      # ── CLOUDFRONT: Total Error Rate ─────────────────────────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 22
        width  = 6
        height = 6
        properties = {
          title  = "CloudFront — Total Error Rate (%)"
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          region = "us-east-1"
          metrics = [[
            "AWS/CloudFront", "TotalErrorRate",
            "DistributionId", aws_cloudfront_distribution.frontend.id,
            "Region", "Global"
          ]]
          yAxis = { left = { min = 0, max = 100 } }
        }
      },

      # ── CLOUDFRONT: Cache Hit Rate (enhanced metric) ─────────────────────────
      {
        type   = "metric"
        x      = 18
        y      = 22
        width  = 6
        height = 6
        properties = {
          title  = "CloudFront — Cache Hit Ratio (%)"
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          region = "us-east-1"
          metrics = [[
            "AWS/CloudFront", "CacheHitRate",
            "DistributionId", aws_cloudfront_distribution.frontend.id,
            "Region", "Global"
          ]]
          yAxis = { left = { min = 0, max = 100 } }
        }
      }

    ] # end widgets
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. CLOUDWATCH ALARMS
# ─────────────────────────────────────────────────────────────────────────────

# ── ALARM 1: Payment Service Errors > 3 ─────────────────────────────────────
# Monitors the payment Lambda specifically — highest business impact.
# Fires when error count exceeds 3 within a single 5-minute window.
resource "aws_cloudwatch_metric_alarm" "payment_errors" {
  alarm_name          = "${var.project_name}-payment-service-errors"
  alarm_description   = "Payment Lambda errors exceeded 3 in a 5-minute window. Investigate immediately — orders may be failing."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "${var.project_name}-payment"
  }

  tags = merge(var.common_tags, {
    Alarm   = "PaymentErrors"
    Service = "payment"
  })
}

# ── ALARM 2: API Gateway Latency > 2000ms ───────────────────────────────────
# Uses p99 latency so single slow outliers don't trigger noise.
# Fires when p99 latency exceeds 2000ms over a 5-minute window.
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "${var.project_name}-api-latency-high"
  alarm_description   = "API Gateway p99 latency exceeded 2000ms. Lambda cold starts or DynamoDB slowness may be the cause."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 2000
  treat_missing_data  = "notBreaching"

  metric_name = "Latency"
  namespace   = "AWS/ApiGateway"
  period      = 300
  extended_statistic = "p99"

  dimensions = {
    ApiId = aws_apigatewayv2_api.game_store.id
    Stage = "$default"
  }

  tags = merge(var.common_tags, {
    Alarm   = "APILatency"
    Service = "api-gateway"
  })
}

# ── ALARM 3: Any Lambda Errors > 5 (across all functions) ───────────────────
# Uses a metric math expression to SUM errors across all 6 Lambda functions.
# Fires when the combined error count exceeds 5 in a 5-minute window.
resource "aws_cloudwatch_metric_alarm" "all_lambda_errors" {
  alarm_name          = "${var.project_name}-all-lambda-errors"
  alarm_description   = "Combined errors across all Lambda functions exceeded 5 in a 5-minute window."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5
  treat_missing_data  = "notBreaching"

  # metric_query lets us SUM errors across all 6 functions
  metric_query {
    id          = "total_errors"
    expression  = "SUM(METRICS())"
    label       = "Total Lambda Errors"
    return_data = true
  }

  metric_query {
    id = "m_product"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-product" }
    }
  }

  metric_query {
    id = "m_cart"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-cart" }
    }
  }

  metric_query {
    id = "m_search"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-search" }
    }
  }

  metric_query {
    id = "m_order"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-order" }
    }
  }

  metric_query {
    id = "m_payment"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-payment" }
    }
  }

  metric_query {
    id = "m_wishlist"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "${var.project_name}-wishlist" }
    }
  }

  tags = merge(var.common_tags, {
    Alarm   = "AllLambdaErrors"
    Service = "lambda"
  })
}

# ── ALARM 4: DynamoDB Throttling > 0 (any table) ────────────────────────────
# PAY_PER_REQUEST tables can still throttle under extreme burst conditions.
# We alarm on ANY throttle event (threshold = 0, so > 0 fires the alarm).
# One alarm per table — gives precise signal about which table is affected.

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each = merge(
    { for k, tbl in local.dynamodb_tables : k => tbl.name },
    { orders = "game-orders" }
  )

  alarm_name          = "${var.project_name}-dynamodb-throttle-${each.key}"
  alarm_description   = "DynamoDB table '${each.value}' has throttled requests. Even PAY_PER_REQUEST tables can throttle on extreme bursts."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = each.value
  }

  tags = merge(var.common_tags, {
    Alarm   = "DynamoDBThrottle"
    Service = "dynamodb"
    Table   = each.value
  })
}
