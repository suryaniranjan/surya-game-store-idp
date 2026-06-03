import json
import boto3
import pytest
from decimal import Decimal
from moto import mock_aws

def make_event(path, params=None):
    return {
        "httpMethod": "GET",
        "rawPath": path,
        "path": path,
        "queryStringParameters": params or {}
    }

@pytest.fixture
def table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        t = dynamodb.create_table(
            TableName="game-products",
            KeySchema=[{"AttributeName": "game_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "game_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        t.put_item(Item={"game_id": "g1", "title": "Elden Ring",
            "description": "Open world RPG", "price": Decimal("59.99"),
            "genre": "RPG", "platform": "PC", "rating": "M", "stock": 100})
        t.put_item(Item={"game_id": "g2", "title": "FIFA 24",
            "description": "Football simulation", "price": Decimal("49.99"),
            "genre": "Sports", "platform": "PS5", "rating": "E", "stock": 50})
        t.put_item(Item={"game_id": "g3", "title": "Hades",
            "description": "Roguelike action", "price": Decimal("24.99"),
            "genre": "Action", "platform": "PC", "rating": "T", "stock": 75})
        import search
        import importlib
        importlib.reload(search)
        yield t

def test_search_by_keyword(table):
    from search import lambda_handler
    res = lambda_handler(make_event("/search", {"q": "elden"}), {})
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["count"] == 1
    assert body["results"][0]["title"] == "Elden Ring"

def test_search_by_genre(table):
    from search import lambda_handler
    body = json.loads(lambda_handler(make_event("/search", {"genre": "RPG"}), {})["body"])
    assert body["count"] == 1

def test_search_by_platform(table):
    from search import lambda_handler
    body = json.loads(lambda_handler(make_event("/search", {"platform": "PC"}), {})["body"])
    assert body["count"] == 2

def test_search_by_price_range(table):
    from search import lambda_handler
    body = json.loads(lambda_handler(make_event("/search", {"min_price": "20", "max_price": "50"}), {})["body"])
    assert body["count"] == 2

def test_search_no_results(table):
    from search import lambda_handler
    body = json.loads(lambda_handler(make_event("/search", {"q": "minecraft"}), {})["body"])
    assert body["count"] == 0

def test_search_invalid_price(table):
    from search import lambda_handler
    res = lambda_handler(make_event("/search", {"min_price": "abc"}), {})
    assert res["statusCode"] == 400

def test_get_filters(table):
    from search import lambda_handler
    res = lambda_handler(make_event("/search/filters"), {})
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert "RPG" in body["genres"]
    assert "PC" in body["platforms"]

def test_suggestions(table):
    from search import lambda_handler
    body = json.loads(lambda_handler(make_event("/search/suggestions", {"q": "el"}), {})["body"])
    assert any(s["title"] == "Elden Ring" for s in body["suggestions"])

def test_suggestions_too_short(table):
    from search import lambda_handler
    res = lambda_handler(make_event("/search/suggestions", {"q": "e"}), {})
    assert res["statusCode"] == 400