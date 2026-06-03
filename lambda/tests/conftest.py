import os
import boto3
import pytest
from moto import mock_aws

# Set ALL env vars before any lambda module is imported
os.environ["AWS_DEFAULT_REGION"]    = "ap-southeast-1"
os.environ["AWS_ACCESS_KEY_ID"]     = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"]    = "testing"
os.environ["AWS_SESSION_TOKEN"]     = "testing"
os.environ["CARTS_TABLE"]           = "game-carts"
os.environ["PRODUCTS_TABLE"]        = "game-products"
os.environ["ORDERS_TABLE"]          = "game-orders"
os.environ["S3_BUCKET_NAME"]        = "test-bucket"
os.environ["CART_API_URL"]          = "https://mock-cart-api.com"