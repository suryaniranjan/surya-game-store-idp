import json
import boto3
import os
from decimal import Decimal
from datetime import datetime, timezone

dynamodb         = boto3.resource("dynamodb")
TABLE_NAME       = os.environ.get("WISHLISTS_TABLE", "game-wishlists")
CARTS_TABLE_NAME = os.environ.get("CARTS_TABLE",     "game-carts")

table      = dynamodb.Table(TABLE_NAME)
carts_table= dynamodb.Table(CARTS_TABLE_NAME)

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


def strip_version_prefix(route_key):
    import re
    return re.sub(r'^(\w+) /v\d+', lambda m: m.group(1) + ' ', route_key).rstrip() \
           if re.match(r'^\w+ /v\d+', route_key) else route_key


def get_wishlist(user_id):
    """GET /wishlist/{user_id} — return the user's wishlist"""
    result = table.get_item(Key={"user_id": user_id})
    wishlist = result.get("Item")
    if not wishlist:
        return response(200, {
            "user_id": user_id,
            "items":   [],
            "total_items": 0,
            "message": "Wishlist is empty"
        })
    wishlist["total_items"] = len(wishlist.get("items", []))
    return response(200, wishlist)


def add_to_wishlist(user_id, body):
    """POST /wishlist/{user_id}/items — add a game to wishlist"""
    required = ["game_id", "title", "price"]
    missing  = [f for f in required if f not in body]
    if missing:
        return response(400, {"message": f"Missing fields: {missing}"})

    result   = table.get_item(Key={"user_id": user_id})
    wishlist = result.get("Item", {"user_id": user_id, "items": []})
    items    = wishlist.get("items", [])

    # Prevent duplicates
    if any(i["game_id"] == body["game_id"] for i in items):
        return response(409, {"message": f"'{body['title']}' is already in your wishlist"})

    items.append({
        "game_id":    body["game_id"],
        "title":      body["title"],
        "price":      Decimal(str(body["price"])),
        "image_url":  body.get("image_url", ""),
        "genre":      body.get("genre", ""),
        "platform":   body.get("platform", ""),
        "stock":      int(body.get("stock", 0)),
        "added_at":   datetime.now(timezone.utc).isoformat()
    })

    wishlist["items"] = items
    table.put_item(Item=wishlist)

    return response(200, {
        "message":     f"'{body['title']}' added to wishlist",
        "user_id":     user_id,
        "total_items": len(items)
    })


def remove_from_wishlist(user_id, game_id):
    """DELETE /wishlist/{user_id}/items/{game_id} — remove one item"""
    result   = table.get_item(Key={"user_id": user_id})
    wishlist = result.get("Item")
    if not wishlist:
        return response(404, {"message": "Wishlist not found"})

    original = len(wishlist.get("items", []))
    wishlist["items"] = [i for i in wishlist["items"] if i["game_id"] != game_id]

    if len(wishlist["items"]) == original:
        return response(404, {"message": f"Game '{game_id}' not in wishlist"})

    table.put_item(Item=wishlist)
    return response(200, {
        "message":     "Item removed from wishlist",
        "user_id":     user_id,
        "total_items": len(wishlist["items"])
    })


def move_to_cart(user_id, game_id):
    """
    POST /wishlist/{user_id}/items/{game_id}/move-to-cart
    Removes item from wishlist and adds it to the cart (quantity = 1).
    """
    result   = table.get_item(Key={"user_id": user_id})
    wishlist = result.get("Item")
    if not wishlist:
        return response(404, {"message": "Wishlist not found"})

    target = next((i for i in wishlist.get("items", []) if i["game_id"] == game_id), None)
    if not target:
        return response(404, {"message": f"Game '{game_id}' not in wishlist"})

    if int(target.get("stock", 0)) == 0:
        return response(400, {"message": f"'{target['title']}' is out of stock"})

    cart_result = carts_table.get_item(Key={"user_id": user_id})
    cart        = cart_result.get("Item", {"user_id": user_id, "items": []})
    cart_items  = cart.get("items", [])

    existing_cart_item = next((i for i in cart_items if i["game_id"] == game_id), None)
    if existing_cart_item:
        existing_cart_item["quantity"] = int(existing_cart_item["quantity"]) + 1
    else:
        cart_items.append({
            "game_id":  target["game_id"],
            "title":    target["title"],
            "price":    Decimal(str(target["price"])),
            "quantity": 1
        })

    cart["items"] = cart_items
    carts_table.put_item(Item=cart)

    wishlist["items"] = [i for i in wishlist["items"] if i["game_id"] != game_id]
    table.put_item(Item=wishlist)

    return response(200, {
        "message":              f"'{target['title']}' moved to cart",
        "user_id":              user_id,
        "wishlist_total_items": len(wishlist["items"]),
        "cart_total_items":     len(cart_items)
    })


def clear_wishlist(user_id):
    """DELETE /wishlist/{user_id} — empty the entire wishlist"""
    result = table.get_item(Key={"user_id": user_id})
    if not result.get("Item"):
        return response(404, {"message": "Wishlist not found"})

    table.put_item(Item={"user_id": user_id, "items": []})
    return response(200, {"message": "Wishlist cleared", "user_id": user_id})


def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    route       = strip_version_prefix(event.get("routeKey", ""))
    path_params = event.get("pathParameters") or {}
    user_id     = path_params.get("user_id", "")
    game_id     = path_params.get("game_id", "")
    body        = parse_body(event)

    if body is None:
        return response(400, {"message": "Invalid JSON in request body"})

    if   route == "GET /wishlist/{user_id}":                               return get_wishlist(user_id)
    elif route == "POST /wishlist/{user_id}/items":                        return add_to_wishlist(user_id, body)
    elif route == "DELETE /wishlist/{user_id}/items/{game_id}":            return remove_from_wishlist(user_id, game_id)
    elif route == "POST /wishlist/{user_id}/items/{game_id}/move-to-cart": return move_to_cart(user_id, game_id)
    elif route == "DELETE /wishlist/{user_id}":                            return clear_wishlist(user_id)
    else:
        return response(404, {"message": f"Route not found: {route}"})