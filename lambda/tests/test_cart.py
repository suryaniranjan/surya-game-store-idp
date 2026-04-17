import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch


def make_event(route, path_params=None, body=None):
    return {
        "routeKey": route,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else None
    }

@pytest.fixture
def table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        t = dynamodb.create_table(
            TableName="game-carts",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        import cart
        import importlib
        importlib.reload(cart)
        yield t

def test_get_empty_cart(table):
    from cart import lambda_handler
    res = lambda_handler(make_event("GET /cart/{user_id}", {"user_id": "u1"}), {})
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["items"] == []

def test_add_to_cart(table):
    from cart import lambda_handler
    res = lambda_handler(make_event(
        "POST /cart/{user_id}/items", {"user_id": "u1"},
        {"game_id": "g1", "title": "Elden Ring", "price": 59.99, "quantity": 1}
    ), {})
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["total_items"] == 1

def test_add_duplicate_increases_quantity(table):
    from cart import lambda_handler
    payload = {"game_id": "g1", "title": "Elden Ring", "price": 59.99, "quantity": 1}
    event = make_event("POST /cart/{user_id}/items", {"user_id": "u1"}, payload)
    lambda_handler(event, {})
    lambda_handler(event, {})
    res = lambda_handler(make_event("GET /cart/{user_id}", {"user_id": "u1"}), {})
    assert json.loads(res["body"])["items"][0]["quantity"] == 2

def test_remove_from_cart(table):
    from cart import lambda_handler
    lambda_handler(make_event(
        "POST /cart/{user_id}/items", {"user_id": "u1"},
        {"game_id": "g1", "title": "Elden Ring", "price": 59.99, "quantity": 1}
    ), {})
    res = lambda_handler(make_event(
        "DELETE /cart/{user_id}/items/{game_id}", {"user_id": "u1", "game_id": "g1"}
    ), {})
    assert res["statusCode"] == 200

def test_clear_cart(table):
    from cart import lambda_handler
    lambda_handler(make_event(
        "POST /cart/{user_id}/items", {"user_id": "u1"},
        {"game_id": "g1", "title": "Elden Ring", "price": 59.99, "quantity": 1}
    ), {})
    res = lambda_handler(make_event("DELETE /cart/{user_id}", {"user_id": "u1"}), {})
    assert res["statusCode"] == 200

def test_add_missing_fields(table):
    from cart import lambda_handler
    res = lambda_handler(make_event(
        "POST /cart/{user_id}/items", {"user_id": "u1"}, {"game_id": "g1"}
    ), {})
    assert res["statusCode"] == 400

def test_remove_from_empty_cart(table):
    from cart import lambda_handler
    res = lambda_handler(make_event(
        "DELETE /cart/{user_id}/items/{game_id}", {"user_id": "u1", "game_id": "g1"}
    ), {})
    assert res["statusCode"] == 404