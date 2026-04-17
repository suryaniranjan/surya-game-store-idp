# GameVault — Online Game Store

A full-stack serverless e-commerce platform for browsing and purchasing games, built with vanilla HTML/CSS/JS and deployed on AWS using Terraform.

🌐 **Live Demo:** https://d1oh72turybrvm.cloudfront.net

---

## 📸 Preview

> GameVault lets users browse games by genre, platform, and rating — add them to cart, and place orders. Admins can manage products and track all orders.

---

## ✨ Features

- 🎮 **Game Catalog** — browse all games with cover art, genre, platform, and price
- 🔍 **Advanced Search** — filter by title, genre, platform, rating; autocomplete suggestions
- 🛒 **Cart Management** — add/remove games, update quantities, live order summary
- 📦 **Order Tracking** — place orders and track status: Placed → Confirmed → Shipped → Delivered
- 👤 **Admin Panel** — add, edit, and delete products; manage all orders
- ⚡ **Serverless Backend** — Python Lambda microservices with zero server maintenance
- 🌍 **CDN Delivery** — static frontend served via CloudFront for fast global access

---

## 🏗️ Architecture

```
                    ┌──────────────────────────────────┐
                    │           User Browser            │
                    └────────────────┬─────────────────┘
                                     │ HTTPS
                    ┌────────────────▼─────────────────┐
                    │       AWS CloudFront (CDN)        │
                    │  https://d1oh72turybrvm.          │
                    │         cloudfront.net            │
                    └───────┬──────────────┬────────────┘
                            │              │
            ┌───────────────▼──┐  ┌────────▼──────────────────┐
            │    S3 Bucket     │  │   API Gateway (HTTP API)   │
            │ game-store-      │  │   game-store-api           │
            │ frontend-        │  │   (h4b0tuf5u4)             │
            │ 726101441380     │  │                            │
            └──────────────────┘  └────────┬──────────────────┘
                                           │
               ┌───────────────────────────┼──────────────────────────┐
               │              AWS Lambda (Python 3.12)                 │
               │                                                       │
               │  ┌─────────────────┐    ┌──────────────────────┐    │
               │  │ product service │    │    cart service      │    │
               │  │ CRUD, catalog   │    │  add/remove/update   │    │
               │  └────────┬────────┘    └──────────┬───────────┘    │
               │           │                        │                 │
               │  ┌────────▼────────┐    ┌──────────▼───────────┐    │
               │  │  order service  │    │    search service     │    │
               │  │  place / track  │    │  filters, suggestions │    │
               │  │  cancel orders  │    │  full-text search     │    │
               │  └─────────────────┘    └──────────────────────┘    │
               └───────────────────────────┬──────────────────────────┘
                                           │
               ┌───────────────────────────▼──────────────────────────┐
               │                   AWS DynamoDB                        │
               │                                                       │
               │   game-products  │  game-carts  │  game-orders        │
               └───────────────────────────────────────────────────────┘

               ┌───────────────────────────────────────────────────────┐
               │        IAM (least-privilege roles per Lambda)         │
               └───────────────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| HTML5 / CSS3 | Structure & styling |
| Vanilla JavaScript | Cart logic, API calls, DOM interactions |

### Backend

| Technology | Purpose |
|---|---|
| AWS Lambda (Python 3.12) | Serverless microservices |
| AWS API Gateway (HTTP API) | REST API routing |
| AWS DynamoDB | NoSQL database |

### Infrastructure (Terraform)

| Resource | Name / Details |
|---|---|
| Region | ap-southeast-1 (Singapore) |
| S3 Bucket | `game-store-frontend-726101441380` |
| API Gateway | `game-store-api` (`h4b0tuf5u4`) |
| DynamoDB Tables | `game-products`, `game-carts`, `game-orders` |
| CloudFront | CDN with HTTPS |

---

## 📁 Project Structure

```
game-store-infra/
├── frontend/                  # Static frontend
│   ├── index.html             # Game store / product listing
│   ├── admin.html             # Admin panel
│   ├── cart.html              # Cart & checkout
│   ├── orders.html            # Order tracking
│   ├── auth.js                # Auth helpers
│   ├── common.js              # Shared utilities
│   ├── config.js              # API base URL config
│   └── styles.css             # Global styles
│
├── lambda/                    # Python Lambda functions
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_cart.py
│   │   ├── test_order.py
│   │   ├── test_product.py
│   │   └── test_search.py
│   ├── cart.py
│   ├── order.py
│   ├── product.py
│   └── search.py
│
├── main.tf                    # Root Terraform config
├── variables.tf
├── outputs.tf
├── frontend.tf                # S3 + CloudFront
├── terraform.tfvars           # Your values (gitignored)
└── deploy-frontend.bat        # Windows deploy script
```

---

## 📡 API Reference

**Base URL:** `https://h4b0tuf5u4.execute-api.ap-southeast-1.amazonaws.com`

### Root
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |

### Games
| Method | Endpoint | Description |
|---|---|---|
| GET | `/games` | List all games |
| POST | `/games` | Create a new game (Admin) |
| GET | `/games/{game_id}` | Get a single game |
| PUT | `/games/{game_id}` | Update a game (Admin) |
| DELETE | `/games/{game_id}` | Delete a game (Admin) |

### Cart
| Method | Endpoint | Description |
|---|---|---|
| GET | `/cart/{user_id}` | Get cart for a user |
| DELETE | `/cart/{user_id}` | Clear entire cart |
| POST | `/cart/{user_id}/items` | Add item to cart |
| DELETE | `/cart/{user_id}/items/{game_id}` | Remove a specific item |

### Orders
| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders` | Place a new order |
| GET | `/orders` | List all orders |
| DELETE | `/orders/{order_id}` | Cancel an order |

### Search
| Method | Endpoint | Description |
|---|---|---|
| GET | `/search` | Search games by title, genre, platform, rating |
| GET | `/search/suggestions` | Autocomplete suggestions |
| GET | `/search/filters` | Get available filter options |

---

## 🗄️ DynamoDB Tables

### `game-products`
Stores the game catalog.

| Attribute | Type | Description |
|---|---|---|
| `game_id` | String (PK) | Unique game identifier |
| `title` | String | Game title |
| `genre` | String | e.g. Action, RPG, Indie |
| `platform` | String | e.g. PC, PS5 |
| `price` | Number | Price in USD |
| `rating` | Number | Rating score |
| `image_url` | String | Cover art URL |

### `game-carts`
Stores per-user cart state.

| Attribute | Type | Description |
|---|---|---|
| `user_id` | String (PK) | User identifier |
| `game_id` | String (SK) | Game in cart |
| `quantity` | Number | Quantity |

### `game-orders`
Stores placed orders.

| Attribute | Type | Description |
|---|---|---|
| `order_id` | String (PK) | Unique order identifier |
| `user_id` | String | User who placed the order |
| `items` | List | List of games ordered |
| `status` | String | Placed / Confirmed / Shipped / Delivered |
| `created_at` | String | Order timestamp |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Terraform 1.5+
- AWS CLI configured (`aws configure`)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd game-store-infra
```

### 2. Set up Terraform variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Fill in your AWS values
```

### 3. Deploy AWS infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 4. Deploy frontend

```bash
# Windows
deploy-frontend.bat

# Or manually
aws s3 sync frontend/ s3://game-store-frontend-726101441380 --delete
```

### 5. Invalidate CloudFront cache

```bash
aws cloudfront create-invalidation \
  --distribution-id $(terraform output -raw cloudfront_id) \
  --paths "/*"
```

---

## 🧪 Running Tests

```bash
cd lambda
python -m pytest tests/ -v

# Run a specific service
python -m pytest tests/test_product.py -v
python -m pytest tests/test_cart.py -v
python -m pytest tests/test_order.py -v
python -m pytest tests/test_search.py -v
```

---

## 🔑 Environment Variables

Fill in `terraform.tfvars` (never commit this file — it's in `.gitignore`):

```hcl
aws_region       = "ap-southeast-1"
environment      = "dev"
project_name     = "game-store"
lambda_runtime   = "python3.12"
lambda_timeout   = 30
lambda_memory    = 256
```

---

## 🔒 Security

- IAM roles with least-privilege access scoped per Lambda function
- HTTPS enforced end-to-end via CloudFront
- DynamoDB access restricted to Lambda IAM roles only
- All config managed via `terraform.tfvars` (never hardcoded)

---

## 👨‍💻 Author

**Surya Niranjan**

- GitHub: [@suryaniranjan](https://github.com/suryaniranjan)

Built with HTML/CSS/JS, Python 3.12, and AWS Serverless — deployed via Terraform
