import json
import boto3
import os
import uuid
from datetime import datetime
import urllib.request
from decimal import Decimal

dynamodb       = boto3.resource("dynamodb")
table          = dynamodb.Table(os.environ["ORDERS_TABLE"])
CART_API_URL   = os.environ["CART_API_URL"]
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "game-products")
products_table = dynamodb.Table(PRODUCTS_TABLE)


def strip_version_prefix(route_key):
    """
    Strips /v1 (or any /vN) prefix from routeKey so existing
    routing logic stays unchanged.
    e.g. "GET /v1/orders" -> "GET /orders"
    """
    import re
    return re.sub(r'^(\w+) /v\d+', lambda m: m.group(1) + ' ', route_key).rstrip() \
           if re.match(r'^\w+ /v\d+', route_key) else route_key


# ── Router ────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    # ── Strip /v1 prefix from routeKey ───────────────────────────────────────
    route_key   = strip_version_prefix(event.get("routeKey", ""))
    # ─────────────────────────────────────────────────────────────────────────

    path_params = event.get("pathParameters") or {}

    if   route_key == "POST /orders":                  return place_order(event)
    elif route_key == "GET /orders":                   return get_orders(event)
    elif route_key == "DELETE /orders/{order_id}":     return cancel_order(event, path_params)
    elif route_key == "GET /admin/orders":             return admin_get_all_orders(event)
    elif route_key == "PUT /orders/{order_id}/status": return update_order_status(event, path_params)
    else:
        return resp(405, {"error": "Method not allowed"})


# ── POST /orders ──────────────────────────────────────────────────────────────
def place_order(event):
    try:
        body    = json.loads(event.get("body") or "{}")
        user_id = body.get("user_id")
        if not user_id:
            return resp(400, {"error": "user_id is required"})

        # 1. Fetch cart
        cart_url = f"{CART_API_URL}/cart/{user_id}"
        req = urllib.request.Request(cart_url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                cart_data = json.loads(res.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"Cart API HTTP error {e.code}: {error_body}")
            return resp(502, {"error": f"Cart service returned {e.code}"})
        except urllib.error.URLError as e:
            print(f"Cart API unreachable: {e.reason}")
            return resp(502, {"error": "Cart service unreachable"})

        cart_items = cart_data.get("items", [])
        if not cart_items:
            return resp(400, {"error": "Cart is empty"})

        # 2. Validate stock
        stock_errors = []
        for item in cart_items:
            game_id = item.get("game_id")
            qty     = int(item.get("quantity", 1))
            product = products_table.get_item(Key={"game_id": game_id}).get("Item")
            if not product:
                stock_errors.append(f"'{item.get('title', game_id)}' no longer exists in store")
                continue
            if int(product.get("stock", 0)) < qty:
                available = int(product.get("stock", 0))
                stock_errors.append(
                    f"'{product['title']}' — only {available} left (you requested {qty})"
                )

        if stock_errors:
            return resp(400, {"error": "Some items are unavailable", "details": stock_errors})

        # 3. Deduct stock with rollback on failure
        deducted = []
        for item in cart_items:
            game_id = item.get("game_id")
            qty     = int(item.get("quantity", 1))
            try:
                products_table.update_item(
                    Key={"game_id": game_id},
                    UpdateExpression="SET stock = stock - :qty",
                    ConditionExpression="stock >= :qty",
                    ExpressionAttributeValues={":qty": qty}
                )
                deducted.append(item)
            except Exception as e:
                _restore_stock(deducted)
                return resp(409, {"error": f"Stock conflict, please retry. Detail: {e}"})

        # 4. Calculate total
        total = sum(
            Decimal(str(item.get("price", 0))) * int(item.get("quantity", 1))
            for item in cart_items
        )

        # 5. Save order
        order_id           = str(uuid.uuid4())
        cart_items_decimal = _convert_to_decimal(cart_items)
        order = {
            "order_id":   order_id,
            "user_id":    user_id,
            "items":      cart_items_decimal,
            "total":      str(round(total, 2)),
            "status":     "PLACED",
            "created_at": datetime.utcnow().isoformat(),
        }
        table.put_item(Item=order)

        # 6. Clear cart (non-fatal)
        try:
            clear_req = urllib.request.Request(
                f"{CART_API_URL}/cart/{user_id}", method="DELETE"
            )
            urllib.request.urlopen(clear_req, timeout=5)
        except Exception as e:
            print(f"Warning: could not clear cart: {e}")

        # Return response with serializable items
        order_response = {**order, "items": cart_items}
        return resp(201, {"message": "Order placed successfully", "order": order_response})

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

        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if not existing:
            return resp(404, {"error": "Order not found"})

        if existing.get("status") != "PLACED":
            return resp(400, {"error": "Only pending (PLACED) orders can be cancelled"})

        _restore_stock(existing.get("items", []))

        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "CANCELLED",
                ":u": datetime.utcnow().isoformat()
            }
        )
        return resp(200, {"message": "Order cancelled", "order_id": order_id})

    except Exception as e:
        print(f"cancel_order error: {e}")
        return resp(500, {"error": str(e)})


# ── GET /admin/orders ─────────────────────────────────────────────────────────
def admin_get_all_orders(event):
    try:
        params        = event.get("queryStringParameters") or {}
        status_filter = params.get("status")

        result = table.scan()
        orders = result.get("Items", [])
        while "LastEvaluatedKey" in result:
            result = table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
            orders.extend(result.get("Items", []))

        if status_filter:
            orders = [o for o in orders if o.get("status") == status_filter.upper()]

        orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
        return resp(200, {"orders": orders, "count": len(orders)})

    except Exception as e:
        print(f"admin_get_all_orders error: {e}")
        return resp(500, {"error": str(e)})


# ── PUT /orders/{order_id}/status ─────────────────────────────────────────────
def update_order_status(event, path_params):
    try:
        order_id   = path_params.get("order_id")
        body       = json.loads(event.get("body") or "{}")
        new_status = (body.get("status") or "").upper()

        if not order_id:
            return resp(400, {"error": "order_id is required"})

        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if not existing:
            return resp(404, {"error": "Order not found"})

        current_status = existing.get("status", "PLACED")

        allowed = {"PLACED": ["DELIVERED", "REJECTED"]}
        if new_status not in allowed.get(current_status, []):
            return resp(400, {
                "error": f"Cannot transition order from '{current_status}' to '{new_status}'"
            })

        if new_status == "REJECTED":
            _restore_stock(existing.get("items", []))

        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": new_status,
                ":u": datetime.utcnow().isoformat()
            }
        )
        return resp(200, {
            "message":  f"Order updated to {new_status}",
            "order_id": order_id,
            "status":   new_status
        })

    except Exception as e:
        print(f"update_order_status error: {e}")
        return resp(500, {"error": str(e)})


# ── Helpers ───────────────────────────────────────────────────────────────────
def _restore_stock(items):
    for item in items:
        game_id = item.get("game_id")
        qty     = int(item.get("quantity", 1))
        try:
            products_table.update_item(
                Key={"game_id": game_id},
                UpdateExpression="SET stock = stock + :qty",
                ExpressionAttributeValues={":qty": qty}
            )
        except Exception as e:
            print(f"Warning: could not restore stock for {game_id}: {e}")


def _convert_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_to_decimal(i) for i in obj]
    return obj


def resp(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }
