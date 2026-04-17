import json
import boto3
import uuid
import os
import base64
from decimal import Decimal

# ── AWS clients ───────────────────────────────────────────────────────────────
dynamodb  = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

TABLE_NAME  = os.environ.get("PRODUCTS_TABLE", "game-products")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "surya-games-store-images")
S3_BASE_URL = f"https://{BUCKET_NAME}.s3.amazonaws.com"

table = dynamodb.Table(TABLE_NAME)


# ── Helpers ───────────────────────────────────────────────────────────────────
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


# ── S3 Image Upload ───────────────────────────────────────────────────────────
def upload_image_to_s3(image_data, game_id, content_type="image/jpeg"):
    """
    Accepts base64 string (with or without data URL prefix).
    Uploads to S3 under products/{game_id}/{uuid}.ext
    Returns the public image URL.
    """
    try:
        # Strip data URL prefix if present e.g. "data:image/jpeg;base64,..."
        if "," in image_data:
            image_data = image_data.split(",")[1]

        image_bytes = base64.b64decode(image_data)

        ext_map = {
            "image/jpeg": ".jpg",
            "image/jpg":  ".jpg",
            "image/png":  ".png",
            "image/webp": ".webp",
            "image/gif":  ".gif"
        }
        ext       = ext_map.get(content_type.lower(), ".jpg")
        s3_key    = f"products/{game_id}/{uuid.uuid4()}{ext}"

        s3_client.put_object(
            Bucket=      BUCKET_NAME,
            Key=         s3_key,
            Body=        image_bytes,
            ContentType= content_type
        )

        return f"{S3_BASE_URL}/{s3_key}"

    except Exception as e:
        print(f"[ERROR] S3 upload failed: {str(e)}")
        return None


# ── Game CRUD ─────────────────────────────────────────────────────────────────
def get_all_games():
    """GET /games — returns all games in the store."""
    result = table.scan()
    items  = result.get("Items", [])
    return response(200, {"games": items, "count": len(items)})


def get_game(game_id):
    """GET /games/{game_id} — returns one game by ID."""
    result = table.get_item(Key={"game_id": game_id})
    item   = result.get("Item")
    if not item:
        return response(404, {"message": f"Game '{game_id}' not found"})
    return response(200, item)


def create_game(body):
    """
    POST /games — adds a new game.
    
    Send image as base64 in the 'image' field OR
    send a direct URL in 'image_url'.
    
    Required fields: title, description, price, genre, platform, stock
    Optional fields: image (base64), image_content_type, image_url, rating
    """
    required = ["title", "description", "price", "genre", "platform", "stock"]
    missing  = [f for f in required if f not in body]
    if missing:
        return response(400, {"message": f"Missing required fields: {missing}"})

    game_id   = str(uuid.uuid4())
    image_url = body.get("image_url", "")

    # If base64 image provided, upload to S3 and use that URL
    if body.get("image"):
        uploaded_url = upload_image_to_s3(
            image_data   = body["image"],
            game_id      = game_id,
            content_type = body.get("image_content_type", "image/jpeg")
        )
        if not uploaded_url:
            return response(500, {"message": "Image upload to S3 failed"})
        image_url = uploaded_url

    item = {
        "game_id":     game_id,
        "title":       body["title"],
        "description": body["description"],
        "price":       Decimal(str(body["price"])),
        "genre":       body["genre"],
        "platform":    body["platform"],
        "stock":       int(body["stock"]),
        "image_url":   image_url,
        "rating":      body.get("rating", "E")
    }
    table.put_item(Item=item)

    return response(201, {
        "message":   "Game added to store successfully",
        "game_id":   game_id,
        "image_url": image_url
    })


def update_game(game_id, body):
    """
    PUT /games/{game_id} — updates fields of an existing game.
    Pass 'image' (base64) to replace the game image.
    """
    existing = table.get_item(Key={"game_id": game_id}).get("Item")
    if not existing:
        return response(404, {"message": f"Game '{game_id}' not found"})

    allowed_fields = ["title", "description", "price", "genre", "platform",
                      "stock", "image_url", "rating"]
    update_fields  = {k: v for k, v in body.items() if k in allowed_fields}

    # Handle image replacement via base64
    if body.get("image"):
        new_url = upload_image_to_s3(
            image_data   = body["image"],
            game_id      = game_id,
            content_type = body.get("image_content_type", "image/jpeg")
        )
        if not new_url:
            return response(500, {"message": "Image upload to S3 failed"})
        update_fields["image_url"] = new_url

    if not update_fields:
        return response(400, {"message": "No valid fields provided for update"})

    if "price" in update_fields:
        update_fields["price"] = Decimal(str(update_fields["price"]))

    update_expr = "SET " + ", ".join(f"#f_{k} = :{k}" for k in update_fields)
    expr_names  = {f"#f_{k}": k for k in update_fields}
    expr_values = {f":{k}": v for k, v in update_fields.items()}

    table.update_item(
        Key={"game_id": game_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values
    )
    return response(200, {
        "message":        "Game updated successfully",
        "game_id":        game_id,
        "updated_fields": list(update_fields.keys())
    })


def delete_game(game_id):
    """DELETE /games/{game_id} — removes a game from the store."""
    existing = table.get_item(Key={"game_id": game_id}).get("Item")
    if not existing:
        return response(404, {"message": f"Game '{game_id}' not found"})

    table.delete_item(Key={"game_id": game_id})
    return response(200, {"message": "Game deleted successfully", "game_id": game_id})


# ── Lambda entry point ────────────────────────────────────────────────────────
def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    route       = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    game_id     = path_params.get("game_id", "")
    body        = parse_body(event)

    if body is None:
        return response(400, {"message": "Invalid JSON in request body"})

    if   route == "GET /":                   return response(200, {
                                                 "service": "Game Product Service",
                                                 "status":  "running ✅",
                                                 "version": "2.0"
                                             })
    elif route == "GET /games":              return get_all_games()
    elif route == "GET /games/{game_id}":    return get_game(game_id)
    elif route == "POST /games":             return create_game(body)
    elif route == "PUT /games/{game_id}":    return update_game(game_id, body)
    elif route == "DELETE /games/{game_id}": return delete_game(game_id)
    else:
        return response(404, {"message": f"Route not found: {route}"})