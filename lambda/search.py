import json
import boto3
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

dynamodb   = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("PRODUCTS_TABLE", "game-products")
table      = dynamodb.Table(TABLE_NAME)


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


def get_query_params(event):
    """
    Query string params arrive like:
    ?q=elden&genre=RPG&platform=PC&min_price=10&max_price=60
    This safely reads them all into a dict.
    """
    return event.get("queryStringParameters") or {}


def search_games(params):
    """
    GET /search
    Supports: q, genre, platform, min_price, max_price, rating
    All filters are optional and combinable.
    """
    q         = params.get("q", "").strip().lower()
    genre     = params.get("genre", "").strip().lower()
    platform  = params.get("platform", "").strip().lower()
    rating    = params.get("rating", "").strip().upper()
    min_price = params.get("min_price")
    max_price = params.get("max_price")

    # Validate price params if provided
    try:
        min_price = float(min_price) if min_price else None
        max_price = float(max_price) if max_price else None
    except ValueError:
        return response(400, {"message": "min_price and max_price must be numbers"})

    if min_price and max_price and min_price > max_price:
        return response(400, {"message": "min_price cannot be greater than max_price"})

    result = table.scan()
    all_games = result.get("Items", [])


    filtered = []
    for game in all_games:

        # Filter: keyword search across title and description
        if q:
            title       = game.get("title", "").lower()
            description = game.get("description", "").lower()
            # Must appear in either title OR description
            if q not in title and q not in description:
                continue

        # Filter: genre (case-insensitive)
        if genre:
            game_genre = game.get("genre", "").lower()
            if genre not in game_genre:             # "rpg" matches "Action RPG"
                continue

        # Filter: platform (case-insensitive)
        if platform:
            game_platform = game.get("platform", "").lower()
            if platform not in game_platform:       # "pc" matches "PC, Xbox"
                continue

        # Filter: age rating (exact match, uppercased)
        if rating:
            if game.get("rating", "").upper() != rating:
                continue

        # Filter: minimum price
        if min_price is not None:
            if float(game.get("price", 0)) < min_price:
                continue

        # Filter: maximum price
        if max_price is not None:
            if float(game.get("price", 0)) > max_price:
                continue

        filtered.append(game)

    # ── Sort results ────────────────────────────────────────
    # Keyword matches: title matches rank higher than description-only matches
    if q:
        def relevance_score(game):
            title = game.get("title", "").lower()
            return 0 if q in title else 1      # 0 = title match (sorts first)
        filtered.sort(key=relevance_score)
    else:
        # Default sort: alphabetical by title
        filtered.sort(key=lambda g: g.get("title", "").lower())

    # ── Build response ──────────────────────────────────────
    # Tell the caller which filters were applied
    applied_filters = {k: v for k, v in {
        "q": q, "genre": genre, "platform": platform,
        "rating": rating, "min_price": min_price, "max_price": max_price
    }.items() if v is not None and v != ""}

    return response(200, {
        "results":          filtered,
        "count":            len(filtered),
        "total_in_store":   len(all_games),
        "filters_applied":  applied_filters
    })


def get_suggestions(params):
    """
    GET /search/suggestions?q=el
    Returns just game titles that start with the query.
    Used for autocomplete dropdowns in a frontend.
    Minimum 2 characters required to avoid returning everything.
    """
    q = params.get("q", "").strip().lower()

    if len(q) < 2:
        return response(400, {
            "message": "Query must be at least 2 characters for suggestions"
        })

    result    = table.scan()
    all_games = result.get("Items", [])

    # Return titles that START with the typed query
    # e.g. "el" matches "Elden Ring" but not "Hades"
    suggestions = [
        {
            "game_id": g["game_id"],
            "title":   g["title"],
            "price":   g.get("price"),
            "genre":   g.get("genre")
        }
        for g in all_games
        if g.get("title", "").lower().startswith(q)
    ]

    suggestions.sort(key=lambda g: g["title"])

    return response(200, {
        "suggestions": suggestions,
        "count":       len(suggestions),
        "query":       q
    })


def get_filters_metadata():
    """
    GET /search/filters
    Returns all unique genres, platforms, and ratings available in the store.
    Useful for populating filter dropdowns in a frontend.
    """
    result    = table.scan()
    all_games = result.get("Items", [])

    genres    = sorted(set(g.get("genre", "")    for g in all_games if g.get("genre")))
    platforms = sorted(set(g.get("platform", "") for g in all_games if g.get("platform")))
    ratings   = sorted(set(g.get("rating", "")   for g in all_games if g.get("rating")))

    prices = [float(g.get("price", 0)) for g in all_games if g.get("price")]
    price_range = {
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0
    }

    return response(200, {
        "genres":      genres,
        "platforms":   platforms,
        "ratings":     ratings,
        "price_range": price_range,
        "total_games": len(all_games)
    })


# ─────────────────────────────────────────────────────────
# Main Handler
# ─────────────────────────────────────────────────────────
def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    method = (
        event.get("httpMethod") or
        event.get("requestContext", {}).get("http", {}).get("method", "GET")
    )
    path   = event.get("path") or event.get("rawPath", "/")
    params = get_query_params(event)

    # Health check
    if path == "/" or path == "/search" and method == "GET" and not params:
        return response(200, {
            "service":           "Game Search Service",
            "status":            "running ✅",
            "supported_filters": ["q", "genre", "platform",
                                  "rating", "min_price", "max_price"]
        })

    # GET /search/filters — available genres, platforms, ratings
    if path == "/search/filters" and method == "GET":
        return get_filters_metadata()

    # GET /search/suggestions?q=el — autocomplete
    if path == "/search/suggestions" and method == "GET":
        return get_suggestions(params)

    # GET /search?q=elden&genre=RPG — main search
    if path == "/search" and method == "GET":
        return search_games(params)

    return response(404, {"message": f"Route not found: {method} {path}"})