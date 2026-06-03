import json
import boto3
import pytest
from moto import mock_aws

def make_event(route, path_params=None, body=None):
    return {
        "routeKey": route,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else None
    }

SAMPLE_GAME = {
    "title": "Elden Ring", "description": "Open world RPG",
    "price": 59.99, "genre": "RPG", "platform": "PC",
    "stock": 100, "rating": "M"
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
        boto3.client("s3", region_name="ap-southeast-1").create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"}
        )
        import product
        import importlib
        importlib.reload(product)
        yield t

def test_get_all_games_empty(table):
    from product import lambda_handler
    res = lambda_handler(make_event("GET /games"), {})
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["games"] == []
    assert body["count"] == 0

def test_create_game(table):
    from product import lambda_handler
    res = lambda_handler(make_event("POST /games", body=SAMPLE_GAME), {})
    assert res["statusCode"] == 201
    assert "game_id" in json.loads(res["body"])

def test_create_game_missing_fields(table):
    from product import lambda_handler
    res = lambda_handler(make_event("POST /games", body={"title": "Only Title"}), {})
    assert res["statusCode"] == 400

def test_get_game_by_id(table):
    from product import lambda_handler
    game_id = json.loads(
        lambda_handler(make_event("POST /games", body=SAMPLE_GAME), {})["body"]
    )["game_id"]
    res = lambda_handler(make_event("GET /games/{game_id}", {"game_id": game_id}), {})
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["title"] == "Elden Ring"

def test_get_nonexistent_game(table):
    from product import lambda_handler
    res = lambda_handler(make_event("GET /games/{game_id}", {"game_id": "fake-id"}), {})
    assert res["statusCode"] == 404

def test_update_game(table):
    from product import lambda_handler
    game_id = json.loads(
        lambda_handler(make_event("POST /games", body=SAMPLE_GAME), {})["body"]
    )["game_id"]
    res = lambda_handler(make_event("PUT /games/{game_id}", {"game_id": game_id}, {"price": 49.99}), {})
    assert res["statusCode"] == 200

def test_delete_game(table):
    from product import lambda_handler
    game_id = json.loads(
        lambda_handler(make_event("POST /games", body=SAMPLE_GAME), {})["body"]
    )["game_id"]
    res = lambda_handler(make_event("DELETE /games/{game_id}", {"game_id": game_id}), {})
    assert res["statusCode"] == 200

def test_delete_nonexistent_game(table):
    from product import lambda_handler
    res = lambda_handler(make_event("DELETE /games/{game_id}", {"game_id": "fake-id"}), {})
    assert res["statusCode"] == 404