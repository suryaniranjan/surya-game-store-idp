<div align="center">

# 🎮 GameVault

### *Your Ultimate Game Store — A Cloud-Native Serverless E-Commerce Experience*

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-Visit%20Site-CCFF00?style=for-the-badge)](https://d1oh72turybrvm.cloudfront.net/)
[![AWS](https://img.shields.io/badge/AWS-CloudFront%20%7C%20Lambda%20%7C%20DynamoDB-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Vanilla JS](https://img.shields.io/badge/JavaScript-Vanilla%20JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)](https://terraform.io/)
[![PyTest](https://img.shields.io/badge/PyTest-Tested-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)

---

> *"Gaming is not just a hobby — it's a culture, a community, and a world of its own."*

---

**⚡ Built for Gamers. Powered by the Cloud. Deployed at Scale. ⚡**

</div>

---

## 🌐 Live Demo

**🔗 URL:** [https://d1oh72turybrvm.cloudfront.net/](https://d1oh72turybrvm.cloudfront.net/)

Browse the full game catalogue, add to cart, and experience the complete checkout flow — served blazing fast via **AWS CloudFront CDN** from Singapore.

---

## 🎯 Project Overview

**GameVault** is a full-stack, cloud-native, serverless e-commerce application for browsing and purchasing games. Designed with a **microservice-inspired AWS Lambda architecture**, every business capability is its own independent, deployable service.

The platform supports:
- 🛍️ Full shopping experience for customers — browse, search, wishlist, cart, checkout
- 🔐 Role-based login for **two Users** and one **Admin** with separate access paths
- 💳 Simulated **Razorpay payment gateway** with success/failure flows
- 📦 Real-time order tracking and admin order management
- 🔍 Advanced search with genre, platform, and rating filters
- 📊 Comprehensive observability via **CloudWatch Logs, Dashboards, and Alarms**

All infrastructure is managed via **Terraform (Infrastructure as Code)**, with the frontend served globally through **AWS CloudFront + S3**.

---

## 🏗️ System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │             User Browser                │
                    └──────────────────┬──────────────────────┘
                                       │ HTTPS
                    ┌──────────────────▼──────────────────────┐
                    │         AWS CloudFront CDN              │
                    │  https://d1oh72turybrvm.cloudfront.net  │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │      Amazon S3 — Static Frontend        │
                    │  (Vanilla HTML/CSS/JS + Game Assets)    │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │       API Gateway HTTP API (/v1)        │
                    │   Base: h4b0tuf5u4.execute-api.ap-      │
                    │         southeast-1.amazonaws.com       │
                    └──┬──────────┬──────────┬────────────┬───┘
                       │          │          │            │
          ┌────────────▼──┐  ┌────▼──────┐  ┌▼─────────┐ ┌▼─────────────┐
          │ Product Svc   │  │ Cart Svc  │  │ Order Svc│ │ Payment Svc  │
          │ Catalog,      │  │ Add/Remove│  │ Place,   │ │ Razorpay     │
          │ CRUD, Images  │  │ Update    │  │ Track,   │ │ Simulation   │
          └───────┬───────┘  └─────┬─────┘  │ Cancel   │ └──────┬───────┘
                  │                │        └────┬─────┘        │
          ┌───────▼───────┐        │             │              │
          │ Search Svc    │        │             │              │
          │ Filters,      │        │             │              │
          │ Suggestions   │        │             │              │
          └───────┬───────┘        │             │              │
                  └────────────────┴─────────────┴──────────────┘
                                          │
                    ┌─────────────────────▼───────────────────┐
                    │            Amazon DynamoDB              │
                    │  ┌──────────┐ ┌─────────┐ ┌──────────┐  │
                    │  │ Products │ │  Carts  │ │  Orders  │  │
                    │  │  Table   │ │  Table  │ │  Table   │  │
                    │  └──────────┘ └─────────┘ └──────────┘  │
                    │  ┌──────────┐                           │
                    │  │Wishlists │                           │
                    │  │  Table   │                           │
                    │  └──────────┘                           │
                    └─────────────────────────────────────────┘
                                          │
                    ┌─────────────────────▼───────────────────┐
                    │         Observability Layer             │
                    │  CloudWatch Logs · Dashboard · Alarms   │
                    │         SNS Email Notifications         │
                    └─────────────────────────────────────────┘
                                          │
                    ┌─────────────────────▼───────────────────┐
                    │     Terraform-Managed Infrastructure    │
                    │   main.tf · variables.tf · outputs.tf   │
                    │     frontend.tf · terraform.tfvars      │
                    └─────────────────────────────────────────┘
```

---

## 🔐 Login & Role-Based Access

The platform features a **dedicated Login Page** as the secure entry point with two distinct access paths.

```
                    ┌─────────────────────────────┐
                    │         Login Page           │
                    │       🎮 GameVault           │
                    └──────────────┬──────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                  │
        ┌─────────▼──────────┐            ┌──────────▼─────────┐
        │    👤  USER LOGIN  │            │  🔧  ADMIN LOGIN   │
        │   user1 / user2    │            │       admin         │
        │                    │            │                     │
        │  Access Granted    │            │  Access Granted     │
        │  ─────────────     │            │  ─────────────      │
        │  ✅ Game Catalogue │            │  ✅ Add / Edit /    │
        │  ✅ Search & Filter│            │     Delete Games    │
        │  ✅ Wishlist        │            │  ✅ Stock Management│
        │  ✅ Shopping Cart  │            │  ✅ All Orders View │
        │  ✅ Razorpay Pay   │            │  ✅ Send / Reject   │
        │  ✅ Order Tracking │            │     Orders          │
        └─────────┬──────────┘            └──────────┬─────────┘
                  │                                   │
                  └──────────────┬────────────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │      API Gateway        │
                     │   Lambda Microservices  │
                     │       DynamoDB          │
                     └────────────────────────┘
```

### Credentials

| Username | Password | Role    |
|----------|----------|---------|
| `user`  | `user@123`  | User  |
| `surya`  | `surya@123`  | User  |
| `admin`  | `admin123` | Admin |

> ⚠️ Authentication is frontend-only using `localStorage`. No backend changes required.

### 👤 User Portal
Regular customers get access to the full shopping experience:
- Browse the full game catalogue with cover art, genre, platform, and price
- Search and filter by title, genre, platform, and age rating
- Manage a personal wishlist
- Add games to cart and proceed to checkout
- Complete payment via the simulated Razorpay modal
- Track order status: Pending Payment → Placed → Delivered / Rejected

### 🔧 Admin Portal
Platform administrators have privileged access to:
- Add, edit, and delete games (with S3 image upload)
- View all orders across all users
- Mark orders as **Sent** or **Reject** them
- Monitor inventory stock levels

---

## 🔄 System Flow

```
 1. 🧑  User visits GameVault
         │
         ▼
 2. 🌐  CloudFront CDN serves static frontend (from S3)
         │
         ▼
 3. 🔐  Login Page — User selects their role
         │
    ┌────┴──────┐
    │           │
    ▼           ▼
  User        Admin
    │           │
    ▼           ▼
 4. 🔍  Search Service   → filter games by title, genre, platform, rating
 5. 📦  Product Service  → fetch game catalogue and details
         │
         ▼
 6. 🛒  Cart Service     → add, remove, and update cart items
         │
         ▼
 7. 📋  Order Service    → create order (status: PENDING_PAYMENT)
         │
         ▼
 8. 💳  Payment Service  → initiate Razorpay simulation; verify success/failure
         │
    ┌────┴──────────────────┐
    │                       │
    ▼                       ▼
  Success                Failure
  Order → PLACED         Stock restored
  Admin sees order       Order → PAYMENT_FAILED
         │
         ▼
 9. ⚙️  Admin Dashboard  → Send or Reject the order
         │
         ▼
10. 💾  DynamoDB         → persist all data across all services
         │
         ▼
11. 📊  CloudWatch       → log, monitor, and alert on all activity
         │
         ▼
12. 📧  SNS              → email notification on critical alarms
         │
         ▼
13. ✅  All infrastructure deployed and managed via Terraform
```

---

## 💳 Payment Flow — Razorpay Simulation

One of the platform's key features is the **Razorpay-simulated payment system** — a realistic payment modal with multiple methods and a configurable success/failure outcome.

```
User Clicks "Place Order"
         │
         ▼
┌────────────────────────┐
│   Order Service        │
│  Creates order with    │
│  status: PENDING_PAYMENT│
└──────────┬─────────────┘
           │
           ▼ POST /v1/payments/initiate
┌────────────────────────┐
│   Payment Service      │
│   Generates payment_id │
│   Returns Razorpay     │
│   order object         │
└──────────┬─────────────┘
           │
           ▼ Razorpay Modal Opens
┌────────────────────────┐
│  Payment Methods:      │
│  💳 Card               │
│  📱 UPI (GPay, Paytm)  │
│  🏦 Net Banking        │
│  👛 Wallets            │
│  📅 EMI Plans          │
│                        │
│  [Simulate: ✅ / ❌]   │
└──────────┬─────────────┘
           │
    ┌──────┴──────────┐
    │                 │
    ▼                 ▼
 Success           Failure
    │                 │
    ▼                 ▼
Order → PLACED   Stock Restored
Admin notified   Order → PAYMENT_FAILED
```

**Features:**
- Realistic Razorpay-styled checkout modal (white card, blue header)
- UPI app selector (Google Pay, PhonePe, Paytm, BHIM)
- Saved card selection + new card form
- Net Banking with bank picker
- Wallet options with mock balances
- EMI plan calculator
- Simulated processing animation with delay
- Success and failure result screens
- Stock automatically restored on payment failure

---

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🎮 Game Catalogue | Full game listings with cover art, genre, platform, price, and stock |
| 🔐 Role-Based Auth | Separate login for 2 Users and 1 Admin — frontend `localStorage`-based |
| 🔍 Advanced Search | Filter by title, genre, platform, and age rating with autocomplete |
| ❤️ Wishlist | Save games to wishlist and move them to cart with one click |
| 🛒 Cart Management | Add, remove, and update cart items per user session |
| 📋 Order Lifecycle | Place → Pending Payment → Placed → Delivered / Rejected |
| 💳 Razorpay Gateway | Full payment modal simulation with multiple methods and outcomes |
| 📦 Admin Order Panel | Send or Reject orders; stock restored on rejection |
| 🖼️ S3 Image Upload | Game cover images uploaded to S3 and served via CloudFront |
| ☁️ Global CDN | AWS CloudFront for ultra-fast worldwide delivery |
| 📊 Observability | CloudWatch Logs, Dashboard, Alarms, and SNS notifications |
| ⚙️ Microservices | Five independently deployable, stateless Lambda services |
| 🧪 Tested Services | PyTest-based unit test suite for every Lambda function |
| 🏗️ IaC Deployments | Entire infrastructure declared and managed via Terraform |

---

## 📁 Project Structure

```
game-store-infra/
│
├── frontend/
│   ├── index.html             ← Game catalogue / store
│   ├── admin.html             ← Admin dashboard (products + orders)
│   ├── cart.html              ← Cart + order confirm + Razorpay modal
│   ├── orders.html            ← User order tracking
│   ├── wishlist.html          ← Wishlist management
│   ├── payment.html           ← Standalone payment page (alt flow)
│   ├── login.html             ← Role-based login page
│   ├── auth.js                ← Frontend auth (localStorage, route guards)
│   ├── common.js              ← Shared utilities (toast, apiFetch, gameImageHTML)
│   ├── config.js              ← API base URL config
│   └── styles.css             ← Global dark gaming theme styles
│
├── lambda/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_cart.py
│   │   ├── test_order.py
│   │   ├── test_product.py
│   │   └── test_search.py
│   ├── cart.py                ← Cart microservice
│   ├── order.py               ← Order microservice
│   ├── payment.py             ← Payment microservice (Razorpay simulation)
│   ├── product.py             ← Product microservice (CRUD + S3 images)
│   ├── search.py              ← Search microservice
│   └── wishlist.py            ← Wishlist microservice
│
├── main.tf                    ← Core infrastructure (Lambda, API GW, DynamoDB, IAM)
├── variables.tf               ← Configurable input parameters
├── outputs.tf                 ← Infrastructure outputs (URLs, ARNs)
├── frontend.tf                ← S3 + CloudFront configuration
├── cloudwatch.tf              ← Monitoring and Alarms
├── terraform.tfvars           ← Your values (gitignored)
├── terraform.lock.hcl
└── deploy-frontend.bat        ← Windows one-click frontend deploy script
```

---

## 🧰 Tech Stack

### Frontend
| Technology | Purpose |
|-----------|---------|
| HTML5 / CSS3 | Structure and dark gaming-themed styling |
| Vanilla JavaScript (ES6+) | All UI logic, API calls, DOM interactions |
| Google Fonts (Syne, DM Sans) | Premium typography |
| LocalStorage | Frontend-only auth session management |

**Frontend Features:**
- Responsive dark gaming UI with yellow/orange accent system
- Role-based navigation (User / Admin) rebuilt dynamically from `auth.js`
- Razorpay-style checkout modal with animated processing screens
- Game search with genre, platform, and rating filters
- Wishlist with move-to-cart functionality
- Admin product editor with S3 image upload
- Tabbed order management for users and admins

### Backend
| Technology | Purpose |
|-----------|---------|
| Python 3.12 | AWS Lambda microservice functions |
| boto3 | AWS SDK — DynamoDB, S3 interactions |
| urllib.request | Internal service-to-service calls (order → cart) |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| Terraform | Infrastructure as Code — full AWS lifecycle management |
| AWS Lambda | Serverless compute for all microservices |
| API Gateway (HTTP v2) | Route and manage all REST API calls |
| Amazon DynamoDB | NoSQL database for products, carts, orders, wishlists |
| Amazon S3 | Frontend static hosting + game cover image storage |
| AWS CloudFront | Global CDN for fast, low-latency delivery |
| AWS CloudWatch | Logging, dashboards, and automated alarms |
| AWS SNS | Email notifications on critical alarm triggers |
| AWS IAM | Least-privilege roles and policies per Lambda |

### Testing
| Technology | Purpose |
|-----------|---------|
| PyTest | Unit testing for all Lambda services |
| conftest.py | Shared test fixtures and configuration |

---

## 📡 API Endpoints

**Base URL:** `https://h4b0tuf5u4.execute-api.ap-southeast-1.amazonaws.com`

### 📦 Product Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`    | `/v1/games`              | List all games |
| `POST`   | `/v1/games`              | Create a new game (Admin) |
| `GET`    | `/v1/games/{game_id}`    | Get a specific game |
| `PUT`    | `/v1/games/{game_id}`    | Update a game (Admin) |
| `DELETE` | `/v1/games/{game_id}`    | Delete a game (Admin) |

### 🛒 Cart Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`    | `/v1/cart/{user_id}`                       | Get cart for a user |
| `POST`   | `/v1/cart/{user_id}/items`                 | Add item to cart |
| `DELETE` | `/v1/cart/{user_id}/items/{game_id}`       | Remove a specific item |
| `DELETE` | `/v1/cart/{user_id}`                       | Clear entire cart |

### 📋 Order Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST`   | `/v1/orders`                        | Create order (→ PENDING_PAYMENT) |
| `GET`    | `/v1/orders`                        | Get all orders for a user |
| `DELETE` | `/v1/orders/{order_id}`             | Cancel an order |
| `GET`    | `/v1/admin/orders`                  | Get all orders (Admin) |
| `PUT`    | `/v1/orders/{order_id}/status`      | Update order status (Admin) |

### 💳 Payment Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/payments/initiate`         | Initiate payment, generate payment_id |
| `POST` | `/v1/payments/verify`           | Verify payment (success / failure) |
| `GET`  | `/v1/payments/{payment_id}`     | Get payment status |

### 🔍 Search Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/search`              | Search games by title, genre, platform, rating |
| `GET` | `/v1/search/suggestions`  | Autocomplete suggestions |
| `GET` | `/v1/search/filters`      | Get available filter options |

### ❤️ Wishlist Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`    | `/v1/wishlist/{user_id}`                              | Get wishlist |
| `POST`   | `/v1/wishlist/{user_id}/items`                        | Add to wishlist |
| `DELETE` | `/v1/wishlist/{user_id}/items/{game_id}`              | Remove from wishlist |
| `POST`   | `/v1/wishlist/{user_id}/items/{game_id}/move-to-cart` | Move item to cart |
| `DELETE` | `/v1/wishlist/{user_id}`                             | Clear wishlist |

---

## 📊 Order Status Lifecycle

```
User Places Order
       │
       ▼
  PENDING_PAYMENT  ←── Payment initiated (payment_id assigned)
       │
  ┌────┴──────────────┐
  │                   │
  ▼                   ▼
PLACED            PAYMENT_FAILED
(payment success) (stock restored)
  │
  ├── User cancels → CANCELLED (stock restored)
  │
  └── Admin action:
        ├── Mark Sent    → DELIVERED
        └── Reject       → REJECTED (stock restored)
```

---

## 🗄️ DynamoDB Tables

### `game-products`
| Attribute   | Type   | Description |
|-------------|--------|-------------|
| `game_id`   | String (PK) | Unique game identifier |
| `title`     | String | Game title |
| `genre`     | String | e.g. Action, RPG, Indie |
| `platform`  | String | e.g. PC, PS5, Xbox |
| `price`     | Number | Price in USD |
| `stock`     | Number | Available stock units |
| `rating`    | String | Age rating (E, T, M, AO) |
| `image_url` | String | Cover art URL (S3/CloudFront) |

### `game-carts`
| Attribute  | Type   | Description |
|------------|--------|-------------|
| `user_id`  | String (PK) | User identifier |
| `items`    | List   | List of `{game_id, title, price, quantity}` |

### `game-orders`
| Attribute          | Type   | Description |
|--------------------|--------|-------------|
| `order_id`         | String (PK) | Unique order identifier |
| `user_id`          | String (GSI) | User who placed the order |
| `items`            | List   | List of games ordered |
| `total`            | String | Order total in USD |
| `status`           | String | PENDING_PAYMENT / PLACED / DELIVERED / REJECTED / CANCELLED / PAYMENT_FAILED |
| `payment_id`       | String | Razorpay payment reference |
| `payment_status`   | String | CAPTURED / FAILED |
| `created_at`       | String | ISO timestamp |

### `game-wishlists`
| Attribute | Type   | Description |
|-----------|--------|-------------|
| `user_id` | String (PK) | User identifier |
| `items`   | List   | List of wishlisted `game_id` entries |

---

## 📊 Observability

### CloudWatch Logs
Logs are collected from all Lambda services:
- Product Service
- Cart Service
- Order Service
- Payment Service
- Search Service
- Wishlist Service
- API Gateway access logs

### CloudWatch Dashboard
The centralised dashboard monitors:

| Metric | Service |
|--------|---------|
| Lambda Invocations | All services |
| Lambda Errors | All services |
| Lambda Duration (P99) | All services |
| API Gateway Requests | API Gateway |
| API Gateway Latency | API Gateway |
| DynamoDB Read/Write Capacity | All tables |
| CloudFront Cache Hit Rate | CDN |

### CloudWatch Alarms & SNS

Automated alarms trigger email notifications via SNS:

```
┌────────────────────────────────────────────────┐
│              CloudWatch Alarms                  │
│                                                 │
│  🔴 Payment Errors    → Errors > 3             │
│  🔴 Lambda Errors     → Errors > 5             │
│  🔴 API Latency       → Latency > 2000 ms      │
│  🔴 DynamoDB Throttle → Throttles > 0          │
└───────────────────────┬────────────────────────┘
                        │
                        ▼
               ┌────────────────┐
               │   SNS Topic    │
               └───────┬────────┘
                        │
                        ▼
               📧 Email Notification
```

---

## ☁️ Infrastructure — Terraform

All AWS infrastructure is fully managed via Terraform:

| File | Purpose |
|------|---------|
| `main.tf` | Core infrastructure — Lambda, API Gateway, S3, CloudFront, DynamoDB, IAM |
| `frontend.tf` | S3 bucket + CloudFront distribution for static site |
| `variables.tf` | Configurable input parameters |
| `outputs.tf` | Infrastructure outputs — URLs, ARNs, table names |
| `terraform.tfvars` | Your environment values (gitignored) |

**Key benefits:**
- ✅ Version-controlled infrastructure
- ✅ Fully repeatable deployments
- ✅ Automated resource provisioning
- ✅ Environment consistency across regions

---

## 🪣 AWS S3 Bucket Usage

```
S3 Bucket
├── frontend/            ← Static HTML/CSS/JS (served via CloudFront)
└── products/            ← Game cover images (served via CloudFront CDN)
```

Amazon S3 powers two key capabilities:

- 🖼️ **Game Image Storage** — Cover art uploaded from the Admin panel is stored in S3 and served via CloudFront, enabling fast global media delivery
- 🌐 **Frontend Hosting** — All static frontend files are deployed to S3, with CloudFront as the CDN layer on top

---

## 🧪 Testing

Every Lambda service has **independent unit tests** to ensure reliability in isolation.

```bash
# Run all tests
cd lambda/
python -m pytest tests/ -v

# Run individual service tests
python -m pytest tests/test_product.py -v
python -m pytest tests/test_cart.py -v
python -m pytest tests/test_order.py -v
python -m pytest tests/test_search.py -v
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Terraform 1.5+
- AWS CLI configured (`aws configure`)

### 1. Clone the repository

```bash
git clone https://github.com/suryaniranjan/game-store-infra.git
cd game-store-infra
```

### 2. Set up Terraform variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Fill in your AWS profile, region, bucket name, cart_api_url
```

### 3. Deploy AWS infrastructure

```bash
terraform init
terraform validate
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

## 🔮 Future Improvements

- 🔐 Real authentication — JWT / OAuth2 with Cognito for secure session management
- 📊 Enhanced Admin Dashboard with revenue analytics and charts
- 🛡️ API Gateway rate limiting and request authorisation
- 📩 Order confirmation emails via AWS SES
- 🔔 Real Razorpay integration with live webhook verification
- 📦 CI/CD pipeline — GitHub Actions for automated deploy on every push
- 🌍 Multi-region DynamoDB replication for global availability

---

## 🧠 What I Learned

- ⚡ **Serverless Architecture** — designing and deploying AWS Lambda microservices with isolated responsibilities
- 🏗️ **Infrastructure as Code** — managing full cloud resources declaratively with Terraform
- 🧩 **Microservice Design** — loosely coupled, independently deployable services communicating via HTTP
- 🔄 **Full-Stack System Design** — connecting vanilla JS frontend flows to Lambda backend logic
- 💳 **Payment Workflow Simulation** — implementing Razorpay initiate/verify flow with stock rollback on failure
- 🧪 **Modular Testing** — writing reliable PyTest suites for each microservice
- 📊 **Observability Engineering** — structured logging, CloudWatch dashboards, alarms, and SNS alerting
- 🔐 **Frontend Auth Patterns** — localStorage-based role guards with zero backend dependency

---

## 🌍 Live Deployment

The platform is hosted using **AWS CloudFront CDN** — ensuring fast, low-latency delivery to users across the globe.

🔗 **Live URL:** [https://d1oh72turybrvm.cloudfront.net/](https://d1oh72turybrvm.cloudfront.net/)

---

## 👨‍💻 Author

**Surya Niranjan**

- GitHub: [@suryaniranjan](https://github.com/suryaniranjan)

> *Built with HTML/CSS/JS, Python 3.12, and AWS Serverless — deployed at scale via Terraform* 🎮⚡

---

<div align="center">

⚡ *Built for Gamers. Powered by the Cloud. Deployed at Scale.* ⚡

🎮🟡🟠🎮🟡🟠🎮🟡🟠🎮🟡🟠🎮

</div>
