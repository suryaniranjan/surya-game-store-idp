import json
import boto3
import os
from decimal import Decimal

dynamodb  = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("CARTS_TABLE", "game-carts")
table     = dynamodb.Table(TABLE_NAME)


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=decimal_to_float)
    }


def parse_body(event):
    if event.get("body"):
        try:
            return json.loads(event["body"])
        except Exception:
            return None
    return {}


def get_cart(user_id):
    """GET /cart/{user_id} — returns the user's current cart."""
    result = table.get_item(Key={"user_id": user_id})
    cart = result.get("Item")
    if not cart:
        # Return an empty cart instead of 404 — better UX
        return response(200, {
            "user_id": user_id,
            "items": [],
            "total_items": 0,
            "message": "Cart is empty"
        })
    cart["total_items"] = len(cart.get("items", []))
    return response(200, cart)


def add_to_cart(user_id, body):
    """POST /cart/{user_id}/items — add a game or increase its quantity."""
    required = ["game_id", "title", "price", "quantity"]
    missing = [f for f in required if f not in body]
    if missing:
        return response(400, {"message": f"Missing fields: {missing}"})

    if int(body["quantity"]) < 1:
        return response(400, {"message": "Quantity must be at least 1"})

    # Load existing cart or start a fresh one
    result = table.get_item(Key={"user_id": user_id})
    cart   = result.get("Item", {"user_id": user_id, "items": []})
    items  = cart.get("items", [])

    # If game already in cart → increase quantity; otherwise append
    for item in items:
        if item["game_id"] == body["game_id"]:
            item["quantity"] = int(item["quantity"]) + int(body["quantity"])
            break
    else:
        items.append({
            "game_id":  body["game_id"],
            "title":    body["title"],
            "price":    Decimal(str(body["price"])),
            "quantity": int(body["quantity"])
        })

    cart["items"] = items
    table.put_item(Item=cart)

    return response(200, {
        "message":    f"'{body['title']}' added to cart",
        "user_id":    user_id,
        "total_items": len(items)
    })


def remove_from_cart(user_id, game_id):
    """DELETE /cart/{user_id}/items/{game_id} — remove a specific game from cart."""
    result = table.get_item(Key={"user_id": user_id})
    cart   = result.get("Item")
    if not cart:
        return response(404, {"message": "Cart not found"})

    original_count = len(cart.get("items", []))
    cart["items"]  = [i for i in cart["items"] if i["game_id"] != game_id]

    if len(cart["items"]) == original_count:
        return response(404, {"message": f"Game '{game_id}' not in cart"})

    table.put_item(Item=cart)
    return response(200, {
        "message": "Item removed from cart",
        "user_id": user_id,
        "total_items": len(cart["items"])
    })


def clear_cart(user_id):
    """DELETE /cart/{user_id} — empties the entire cart."""
    result = table.get_item(Key={"user_id": user_id})
    if not result.get("Item"):
        return response(404, {"message": "Cart not found"})

    table.put_item(Item={"user_id": user_id, "items": []})
    return response(200, {"message": "Cart cleared", "user_id": user_id})


def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    route       = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    user_id     = path_params.get("user_id", "")
    game_id     = path_params.get("game_id", "")
    body        = parse_body(event)

    if body is None:
        return response(400, {"message": "Invalid JSON in request body"})

    if   route == "GET /":                                  return response(200, {
                                                                "service": "Game Cart Service",
                                                                "status": "running ✅"
                                                            })
    elif route == "GET /cart/{user_id}":                    return get_cart(user_id)
    elif route == "POST /cart/{user_id}/items":             return add_to_cart(user_id, body)
    elif route == "DELETE /cart/{user_id}/items/{game_id}": return remove_from_cart(user_id, game_id)
    elif route == "DELETE /cart/{user_id}":                 return clear_cart(user_id)
    else:
        return response(404, {"message": f"Route not found: {route}"})