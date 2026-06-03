import json
import boto3
import os
import uuid
from datetime import datetime
from decimal import Decimal
import urllib.request

dynamodb       = boto3.resource("dynamodb")
ORDERS_TABLE   = os.environ["ORDERS_TABLE"]
CART_API_URL   = os.environ["CART_API_URL"]
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "game-products")

table          = dynamodb.Table(ORDERS_TABLE)
products_table = dynamodb.Table(PRODUCTS_TABLE)


def strip_version_prefix(route_key):
    import re
    return re.sub(r'^(\w+) /v\d+', lambda m: m.group(1) + ' ', route_key).rstrip() \
           if re.match(r'^\w+ /v\d+', route_key) else route_key


def lambda_handler(event, context):
    route = strip_version_prefix(event.get("routeKey", ""))
    path_params = event.get("pathParameters") or {}

    if   route == "POST /payment/initiate":               return initiate_payment(event)
    elif route == "POST /payment/confirm":                return confirm_payment(event)
    elif route == "POST /payment/fail":                   return fail_payment(event)
    else:
        return resp(405, {"error": "Method not allowed"})


# ── POST /payment/initiate ────────────────────────────────────────────────────
# Called when user clicks "Proceed to Pay" on cart page.
# Validates cart + stock, creates a PENDING_PAYMENT order, returns order details
# for the Razorpay modal to display. Does NOT deduct stock yet.
def initiate_payment(event):
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
            return resp(502, {"error": f"Cart service returned {e.code}"})
        except urllib.error.URLError as e:
            return resp(502, {"error": "Cart service unreachable"})

        cart_items = cart_data.get("items", [])
        if not cart_items:
            return resp(400, {"error": "Cart is empty"})

        # 2. Validate stock (do not deduct yet)
        stock_errors = []
        for item in cart_items:
            game_id = item.get("game_id")
            qty     = int(item.get("quantity", 1))
            product = products_table.get_item(Key={"game_id": game_id}).get("Item")
            if not product:
                stock_errors.append(f"'{item.get('title', game_id)}' no longer exists")
                continue
            if int(product.get("stock", 0)) < qty:
                available = int(product.get("stock", 0))
                stock_errors.append(
                    f"'{product['title']}' — only {available} left (you need {qty})"
                )

        if stock_errors:
            return resp(400, {"error": "Some items are unavailable", "details": stock_errors})

        # 3. Calculate total
        total = sum(
            Decimal(str(item.get("price", 0))) * int(item.get("quantity", 1))
            for item in cart_items
        )

        # 4. Create order in PENDING_PAYMENT state (no stock deducted)
        order_id           = str(uuid.uuid4())
        payment_id         = f"pay_{uuid.uuid4().hex[:16]}"   # simulated Razorpay payment_id
        cart_items_decimal = _convert_to_decimal(cart_items)

        order = {
            "order_id":   order_id,
            "user_id":    user_id,
            "items":      cart_items_decimal,
            "total":      str(round(total, 2)),
            "status":     "PENDING_PAYMENT",
            "payment_id": payment_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        table.put_item(Item=order)

        # Return enough info for the Razorpay modal
        return resp(201, {
            "order_id":   order_id,
            "payment_id": payment_id,
            "total":      str(round(total, 2)),
            "items":      cart_items,
            "message":    "Payment initiated"
        })

    except Exception as e:
        print(f"initiate_payment error: {e}")
        return resp(500, {"error": str(e)})


# ── POST /payment/confirm ─────────────────────────────────────────────────────
# Called after user clicks "Pay Now" in the simulated Razorpay modal.
# Deducts stock, moves order to PLACED, clears cart.
def confirm_payment(event):
    try:
        body       = json.loads(event.get("body") or "{}")
        order_id   = body.get("order_id")
        payment_id = body.get("payment_id")
        user_id    = body.get("user_id")

        if not order_id or not payment_id or not user_id:
            return resp(400, {"error": "order_id, payment_id and user_id are required"})

        # 1. Fetch the pending order
        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if not existing:
            return resp(404, {"error": "Order not found"})
        if existing.get("status") != "PENDING_PAYMENT":
            return resp(400, {"error": f"Order is already {existing.get('status')}"})

        cart_items = existing.get("items", [])

        # 2. Re-validate stock (someone else may have bought in the meantime)
        stock_errors = []
        for item in cart_items:
            game_id = item.get("game_id")
            qty     = int(item.get("quantity", 1))
            product = products_table.get_item(Key={"game_id": game_id}).get("Item")
            if not product or int(product.get("stock", 0)) < qty:
                available = int(product.get("stock", 0)) if product else 0
                stock_errors.append(
                    f"'{item.get('title', game_id)}' — only {available} left"
                )

        if stock_errors:
            # Mark as PAYMENT_FAILED (stock issue after payment initiated)
            table.update_item(
                Key={"order_id": order_id},
                UpdateExpression="SET #s = :s, updated_at = :u, failure_reason = :r",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": "PAYMENT_FAILED",
                    ":u": datetime.utcnow().isoformat(),
                    ":r": "Stock unavailable at time of payment"
                }
            )
            return resp(409, {"error": "Stock changed — payment cannot be completed", "details": stock_errors})

        # 3. Deduct stock with rollback
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
                table.update_item(
                    Key={"order_id": order_id},
                    UpdateExpression="SET #s = :s, updated_at = :u, failure_reason = :r",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={
                        ":s": "PAYMENT_FAILED",
                        ":u": datetime.utcnow().isoformat(),
                        ":r": f"Stock conflict: {str(e)}"
                    }
                )
                return resp(409, {"error": f"Stock conflict, please retry."})

        # 4. Move order to PLACED
        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u, payment_id = :p",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "PLACED",
                ":u": datetime.utcnow().isoformat(),
                ":p": payment_id
            }
        )

        # 5. Clear cart (non-fatal)
        try:
            clear_req = urllib.request.Request(
                f"{CART_API_URL}/cart/{user_id}", method="DELETE"
            )
            urllib.request.urlopen(clear_req, timeout=5)
        except Exception as e:
            print(f"Warning: could not clear cart: {e}")

        return resp(200, {
            "message":  "Payment successful — order placed",
            "order_id": order_id,
            "status":   "PLACED"
        })

    except Exception as e:
        print(f"confirm_payment error: {e}")
        return resp(500, {"error": str(e)})


# ── POST /payment/fail ────────────────────────────────────────────────────────
# Called when user clicks "Fail Payment" in the simulated modal.
# Marks order as PAYMENT_FAILED. Stock was never deducted.
def fail_payment(event):
    try:
        body     = json.loads(event.get("body") or "{}")
        order_id = body.get("order_id")

        if not order_id:
            return resp(400, {"error": "order_id is required"})

        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if not existing:
            return resp(404, {"error": "Order not found"})
        if existing.get("status") != "PENDING_PAYMENT":
            return resp(400, {"error": f"Order is already {existing.get('status')}"})

        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u, failure_reason = :r",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "PAYMENT_FAILED",
                ":u": datetime.utcnow().isoformat(),
                ":r": "Payment declined by user"
            }
        )

        return resp(200, {
            "message":  "Payment failed — order not placed",
            "order_id": order_id,
            "status":   "PAYMENT_FAILED"
        })

    except Exception as e:
        print(f"fail_payment error: {e}")
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