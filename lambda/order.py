import json
import boto3
import os
import uuid
from datetime import datetime
import urllib.request
from decimal import Decimal 

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(os.environ["ORDERS_TABLE"])
CART_API_URL = os.environ["CART_API_URL"]


def lambda_handler(event, context):
    # v2 HTTP API uses routeKey e.g. "POST /orders"
    route_key   = event.get("routeKey", "")
    method      = route_key.split(" ")[0] if route_key else event.get("httpMethod", "")
    path        = event.get("rawPath", event.get("path", ""))
    path_params = event.get("pathParameters") or {}

    if method == "POST":
        return place_order(event)
    elif method == "GET":
        return get_orders(event)
    elif method == "DELETE":
        return cancel_order(event, path_params)
    else:
        return resp(405, {"error": "Method not allowed"})


# ── POST /orders ──────────────────────────────────────────────────────────────
def place_order(event):
    try:
        body    = json.loads(event.get("body") or "{}")
        user_id = body.get("user_id")

        if not user_id:
            return resp(400, {"error": "user_id is required"})

        # 1. Fetch cart from Cart service
        cart_url = f"{CART_API_URL}/cart/{user_id}"
        req = urllib.request.Request(cart_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            cart_data = json.loads(res.read().decode())

        cart_items = cart_data.get("items", [])
        if not cart_items:
            return resp(400, {"error": "Cart is empty"})

        # 2. Calculate total
        total = sum(
            Decimal(str(item.get("price", 0))) * int(item.get("quantity", 1))
            for item in cart_items
        )

        # 3. Save order to DynamoDB
        order_id = str(uuid.uuid4())

        def convert_to_decimal(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            if isinstance(obj, dict):
                return {k: convert_to_decimal(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_to_decimal(i) for i in obj]
            return obj
        
        cart_items_decimal = convert_to_decimal(cart_items)

        order = {
            "order_id":   order_id,
            "user_id":    user_id,
            "items":      cart_items_decimal,
            "total":      str(round(total, 2)),
            "status":     "PLACED",
            "created_at": datetime.utcnow().isoformat(),
        }
        table.put_item(Item=order)

        # 4. Clear the cart after successful order
        clear_url = f"{CART_API_URL}/cart/{user_id}"
        clear_req = urllib.request.Request(clear_url, method="DELETE")
        try:
            urllib.request.urlopen(clear_req, timeout=5)
        except Exception as clear_err:
            # Non-fatal — order is already saved
            print(f"Warning: could not clear cart: {clear_err}")

        return resp(201, {"message": "Order placed successfully", "order": order})

    except Exception as e:
        print(f"place_order error: {e}")
        return resp(500, {"error": str(e)})


# ── GET /orders?user_id=xxx ───────────────────────────────────────────────────
def get_orders(event):
    try:
        params  = event.get("queryStringParameters") or {}
        user_id = params.get("user_id")

        if not user_id:
            return resp(400, {"error": "user_id is required"})

        result = table.query(
            IndexName="user_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id),
        )

        orders = result.get("Items", [])
        # Sort newest first in Lambda so frontend doesn't have to
        orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)

        return resp(200, {"orders": orders})

    except Exception as e:
        print(f"get_orders error: {e}")
        return resp(500, {"error": str(e)})


# ── DELETE /orders/{order_id} ─────────────────────────────────────────────────
def cancel_order(event, path_params):
    try:
        order_id = path_params.get("order_id")
        if not order_id:
            return resp(400, {"error": "order_id is required"})

        # Check order exists first
        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if not existing:
            return resp(404, {"error": "Order not found"})

        # Hard delete from DynamoDB
        table.delete_item(Key={"order_id": order_id})

        return resp(200, {"message": "Order cancelled and removed", "order_id": order_id})

    except Exception as e:
        print(f"cancel_order error: {e}")
        return resp(500, {"error": str(e)})

# ── Response helper ───────────────────────────────────────────────────────────
def resp(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }