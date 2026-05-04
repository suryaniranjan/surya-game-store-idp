# ─────────────────────────────────────────────────────────────────────────────
# main.tf  —  Game Store Microservices on AWS Lambda + API Gateway
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# ─────────────────────────────────────────────────────────────────────────────
# LOCALS
# ─────────────────────────────────────────────────────────────────────────────

locals {

  dynamodb_tables = {
    products = {
      name     = "game-products"
      hash_key = "game_id"
      env_key  = "PRODUCTS_TABLE"
    }
    carts = {
      name     = "game-carts"
      hash_key = "user_id"
      env_key  = "CARTS_TABLE"
    }
    # ── WISHLIST ──────────────────────────────────────────────────────────────
    wishlists = {
      name     = "game-wishlists"
      hash_key = "user_id"
      env_key  = "WISHLISTS_TABLE"
    }
    # orders is NOT here — it needs a GSI so it has its own resource below
  }

  lambdas = {
    product = {
      source_file = "product.py"
      handler     = "product.lambda_handler"
      description = "Product CRUD service"
      env_vars = {
        PRODUCTS_TABLE = local.dynamodb_tables.products.name
        S3_BUCKET_NAME = var.s3_bucket_name
      }
    }
    cart = {
      source_file = "cart.py"
      handler     = "cart.lambda_handler"
      description = "Cart service"
      env_vars = {
        CARTS_TABLE = local.dynamodb_tables.carts.name
      }
    }
    search = {
      source_file = "search.py"
      handler     = "search.lambda_handler"
      description = "Search & filter service"
      env_vars = {
        PRODUCTS_TABLE = local.dynamodb_tables.products.name
      }
    }
    order = {
      source_file = "order.py"
      handler     = "order.lambda_handler"
      description = "Order service"
      env_vars = {
        ORDERS_TABLE   = aws_dynamodb_table.orders_table.name
        CART_API_URL   = var.cart_api_url
        PRODUCTS_TABLE = local.dynamodb_tables.products.name
      }
    }
    # ── WISHLIST ──────────────────────────────────────────────────────────────
    wishlist = {
      source_file = "wishlist.py"
      handler     = "wishlist.lambda_handler"
      description = "Wishlist service"
      env_vars = {
        WISHLISTS_TABLE = local.dynamodb_tables.wishlists.name
        CARTS_TABLE     = local.dynamodb_tables.carts.name
      }
    }
  }

  api_routes = {
    "GET /"                                     = { lambda_key = "product" }

    # Product service
    "GET /v1/games"                             = { lambda_key = "product" }
    "GET /v1/games/{game_id}"                   = { lambda_key = "product" }
    "POST /v1/games"                            = { lambda_key = "product" }
    "PUT /v1/games/{game_id}"                   = { lambda_key = "product" }
    "DELETE /v1/games/{game_id}"                = { lambda_key = "product" }

    # Cart service
    "GET /v1/cart/{user_id}"                    = { lambda_key = "cart" }
    "POST /v1/cart/{user_id}/items"             = { lambda_key = "cart" }
    "DELETE /v1/cart/{user_id}/items/{game_id}" = { lambda_key = "cart" }
    "DELETE /v1/cart/{user_id}"                 = { lambda_key = "cart" }

    # Search service
    "GET /v1/search"                            = { lambda_key = "search" }
    "GET /v1/search/filters"                    = { lambda_key = "search" }
    "GET /v1/search/suggestions"                = { lambda_key = "search" }

    # Order service
    "GET /v1/orders"                            = { lambda_key = "order" }
    "POST /v1/orders"                           = { lambda_key = "order" }
    "DELETE /v1/orders/{order_id}"              = { lambda_key = "order" }
    "GET /v1/admin/orders"                      = { lambda_key = "order" }
    "PUT /v1/orders/{order_id}/status"          = { lambda_key = "order" }

    # Wishlist service
    "GET /v1/wishlist/{user_id}"                                       = { lambda_key = "wishlist" }
    "POST /v1/wishlist/{user_id}/items"                                = { lambda_key = "wishlist" }
    "DELETE /v1/wishlist/{user_id}/items/{game_id}"                    = { lambda_key = "wishlist" }
    "POST /v1/wishlist/{user_id}/items/{game_id}/move-to-cart"         = { lambda_key = "wishlist" }
    "DELETE /v1/wishlist/{user_id}"                                    = { lambda_key = "wishlist" }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# DYNAMODB
# ─────────────────────────────────────────────────────────────────────────────

# Generic tables (no GSI needed) — products, carts, wishlists
resource "aws_dynamodb_table" "tables" {
  for_each = local.dynamodb_tables

  name         = each.value.name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = each.value.hash_key

  attribute {
    name = each.value.hash_key
    type = "S"
  }

  tags = merge(var.common_tags, { Name = each.value.name })
}

# Orders table — separate because it needs a GSI on user_id
resource "aws_dynamodb_table" "orders_table" {
  name         = "game-orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  tags = merge(var.common_tags, { Name = "game-orders" })
}

# ─────────────────────────────────────────────────────────────────────────────
# IAM
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# products + carts + wishlists tables (all generic tables in the for_each)
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for k, tbl in local.dynamodb_tables : {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
          "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.tables[k].arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
      Resource = "arn:aws:s3:::${var.s3_bucket_name}/products/*"
    }]
  })
}

# orders table + GSI
resource "aws_iam_role_policy" "lambda_orders_dynamodb" {
  name = "${var.project_name}-lambda-orders-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem",
        "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"
      ]
      Resource = [
        aws_dynamodb_table.orders_table.arn,
        "${aws_dynamodb_table.orders_table.arn}/index/*"
      ]
    }]
  })
}

# allow order lambda to read & update stock on the products table
resource "aws_iam_role_policy" "lambda_order_products_access" {
  name = "${var.project_name}-lambda-order-products-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]
      Resource = aws_dynamodb_table.tables["products"].arn
    }]
  })
}

# ── WISHLIST: read/write wishlists + write to carts (for move-to-cart) ────────
resource "aws_iam_role_policy" "lambda_wishlist_dynamodb" {
  name = "${var.project_name}-lambda-wishlist-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
          "dynamodb:DeleteItem", "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.tables["wishlists"].arn
      },
      {
        # move-to-cart needs to read & write the carts table
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem"]
        Resource = aws_dynamodb_table.tables["carts"].arn
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# ZIP ARCHIVES
# ─────────────────────────────────────────────────────────────────────────────

data "archive_file" "lambda_zip" {
  for_each = local.lambdas

  type        = "zip"
  source_file = "${path.module}/lambda/${each.value.source_file}"
  output_path = "${path.module}/.build/${each.key}.zip"
}

# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_lambda_function" "functions" {
  for_each = local.lambdas

  function_name = "${var.project_name}-${each.key}"
  description   = each.value.description
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = each.value.handler
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256

  environment {
    variables = each.value.env_vars
  }

  tags = merge(var.common_tags, { Name = "${var.project_name}-${each.key}" })
}

# ─────────────────────────────────────────────────────────────────────────────
# API GATEWAY (HTTP API v2)
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "game_store" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  description   = "Game Store HTTP API"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  tags = merge(var.common_tags, { Name = "${var.project_name}-api" })
}

resource "aws_apigatewayv2_integration" "lambda_integrations" {
  for_each = local.lambdas

  api_id                 = aws_apigatewayv2_api.game_store.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.functions[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "routes" {
  for_each = local.api_routes

  api_id    = aws_apigatewayv2_api.game_store.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integrations[each.value.lambda_key].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.game_store.id
  name        = "$default"
  auto_deploy = true

  tags = var.common_tags
}

resource "aws_lambda_permission" "api_gw_invoke" {
  for_each = local.lambdas

  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.game_store.execution_arn}/*/*"
}
