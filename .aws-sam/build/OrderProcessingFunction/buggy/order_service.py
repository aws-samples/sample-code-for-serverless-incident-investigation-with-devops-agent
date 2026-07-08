"""Order business logic — BUGGY VARIANT.

This variant introduces a KeyError in create_order by accessing
payload data via dict key instead of Pydantic attribute, causing
HTTP 500 on POST /orders while GET endpoints remain functional.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from app.config import get_config
from app.models.order import OrderCreate, OrderResponse

logger = logging.getLogger(__name__)


def _get_table():
    cfg = get_config()
    dynamodb = boto3.resource("dynamodb", region_name=cfg.AWS_REGION)
    return dynamodb.Table(cfg.DYNAMODB_TABLE_NAME)


def _to_response(item: dict) -> OrderResponse:
    return OrderResponse(
        order_id=item["order_id"],
        customer_id=item["customer_id"],
        product_name=item["product_name"],
        quantity=int(item["quantity"]),
        unit_price=float(item["unit_price"]),
        total_amount=float(item["total_amount"]),
        status=item["status"],
        shipping_address=item["shipping_address"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def create_order(payload: OrderCreate) -> OrderResponse:
    """Create a new order — BUGGY: accesses dict key that doesn't exist."""
    now = datetime.now(timezone.utc).isoformat()
    order_id = f"ord-{uuid.uuid4().hex[:8]}"

    # BUG: Convert payload to dict then access a key that was renamed
    data = payload.model_dump()
    # This line raises KeyError because the key is 'shipping_address'
    # but we're accessing 'delivery_address' which doesn't exist
    address = data["delivery_address"]  # KeyError: 'delivery_address'

    total_amount = round(data["quantity"] * data["unit_price"], 2)

    item = {
        "order_id": order_id,
        "customer_id": data["customer_id"],
        "product_name": data["product_name"],
        "quantity": data["quantity"],
        "unit_price": Decimal(str(data["unit_price"])),
        "total_amount": Decimal(str(total_amount)),
        "status": "pending",
        "shipping_address": address,
        "created_at": now,
        "updated_at": now,
    }

    table = _get_table()
    table.put_item(Item=item)
    return _to_response({**item, "unit_price": float(item["unit_price"]), "total_amount": float(item["total_amount"])})


def get_order(order_id: str) -> OrderResponse | None:
    """Retrieve a single order by ID — unchanged, works correctly."""
    try:
        table = _get_table()
        resp = table.get_item(Key={"order_id": order_id})
    except ClientError as e:
        logger.error("DynamoDB error getting order %s: %s", order_id, e, exc_info=True)
        raise RuntimeError("Failed to get order") from e
    item = resp.get("Item")
    if not item:
        return None
    return _to_response(item)


def list_orders(limit: int = 20) -> list[OrderResponse]:
    """List recent orders — unchanged, works correctly."""
    try:
        table = _get_table()
        resp = table.scan(Limit=limit)
    except ClientError as e:
        logger.error("DynamoDB error listing orders: %s", e, exc_info=True)
        raise RuntimeError("Failed to list orders") from e
    return [_to_response(item) for item in resp.get("Items", [])]
