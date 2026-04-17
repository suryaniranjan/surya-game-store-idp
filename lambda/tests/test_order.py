import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock

MOCK_CART  = {"items": [{"game_id": "g1", "title": "Elden Ring", "price": 59.99, "quantity": 1}]}
EMPTY_CART = {"items": []}

def make_event(route_key, path_params=None, body=None, query_params=None):
    return {
        "routeKey": route_key,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else None,
        "queryStringParameters": query_params or {},
        "rawPath": "/" + route_key.split(" ")[1].lstrip("/").split("/")[0]
    }

def mock_urlopen(cart_data):
    mock_res = MagicMock()
    mock_res.read.return_value = json.dumps(cart_data).encode()
    mock_res.__enter__ = lambda s: s
    mock_res.__exit__ = MagicMock(return_value=False)
    return mock_res

@pytest.fixture
def table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        t = dynamodb.create_table(
            TableName="game-orders",
            KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "order_id", "AttributeType": "S"},
                {"AttributeName": "user_id",  "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "user_id-index",
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"}
            }],
            BillingMode="PAY_PER_REQUEST"
        )
        import order
        import importlib
        importlib.reload(order)
        yield t

def test_place_order_success(table):
    from order import lambda_handler
    with patch("urllib.request.urlopen", return_value=mock_urlopen(MOCK_CART)):
        res = lambda_handler(make_event("POST /orders", body={"user_id": "u1"}), {})
    assert res["statusCode"] == 201
    assert json.loads(res["body"])["message"] == "Order placed successfully"

def test_place_order_missing_user_id(table):
    from order import lambda_handler
    res = lambda_handler(make_event("POST /orders", body={}), {})
    assert res["statusCode"] == 400
    assert json.loads(res["body"])["error"] == "user_id is required"

def test_place_order_empty_cart(table):
    from order import lambda_handler
    with patch("urllib.request.urlopen", return_value=mock_urlopen(EMPTY_CART)):
        res = lambda_handler(make_event("POST /orders", body={"user_id": "u1"}), {})
    assert res["statusCode"] == 400
    assert json.loads(res["body"])["error"] == "Cart is empty"

def test_get_orders(table):
    from order import lambda_handler
    with patch("urllib.request.urlopen", return_value=mock_urlopen(MOCK_CART)):
        lambda_handler(make_event("POST /orders", body={"user_id": "u1"}), {})
    res = lambda_handler(make_event("GET /orders", query_params={"user_id": "u1"}), {})
    assert res["statusCode"] == 200
    assert len(json.loads(res["body"])["orders"]) == 1

def test_get_orders_missing_user_id(table):
    from order import lambda_handler
    res = lambda_handler(make_event("GET /orders"), {})
    assert res["statusCode"] == 400

def test_cancel_order(table):
    from order import lambda_handler
    with patch("urllib.request.urlopen", return_value=mock_urlopen(MOCK_CART)):
        place_res = lambda_handler(make_event("POST /orders", body={"user_id": "u1"}), {})
    order_id = json.loads(place_res["body"])["order"]["order_id"]
    res = lambda_handler(make_event("DELETE /orders/{order_id}", {"order_id": order_id}), {})
    assert res["statusCode"] == 200

def test_cancel_nonexistent_order(table):
    from order import lambda_handler
    res = lambda_handler(make_event("DELETE /orders/{order_id}", {"order_id": "fake-id"}), {})
    assert res["statusCode"] == 404