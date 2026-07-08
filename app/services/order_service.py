# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Order business logic and DynamoDB access."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, ReadTimeoutError

from app.config import get_config
from app.models.order import OrderCreate, OrderResponse

logger = logging.getLogger(__name__)

# Payment validation function name from environment
PAYMENT_VALIDATION_FUNCTION_NAME = os.environ.get("PAYMENT_VALIDATION_FUNCTION_NAME", "")


def _get_request_id() -> str:
    """Get request_id from Lambda context or generate a UUID fallback."""
    # In Lambda, the aws_request_id is available via the context object.
    # Since we're called from FastAPI/Mangum, we don't have direct access to
    # the Lambda context here. Generate a UUID as correlation ID.
    # The Lambda context's aws_request_id is set at the handler level;
    # for cross-service correlation we generate our own.
    return str(uuid.uuid4())


def _validate_payment(order_id: str, customer_id: str, amount: float, request_id: str) -> dict:
    """
    Invoke payment-validation-service synchronously via Lambda SDK.

    Returns the parsed response payload on success (status == "approved").
    Raises RuntimeError on failure (timeout, invocation error, or non-approved status).
    """
    function_name = PAYMENT_VALIDATION_FUNCTION_NAME
    if not function_name:
        logger.error(
            "PAYMENT_VALIDATION_FUNCTION_NAME not configured",
            extra={"request_id": request_id, "endpoint": "POST /orders"},
        )
        raise RuntimeError("Service configuration error")

    cfg = get_config()
    # Create Lambda client with 5-second read timeout
    lambda_client = boto3.client(
        "lambda",
        region_name=cfg.AWS_REGION,
        config=BotoConfig(read_timeout=5, connect_timeout=5, retries={"max_attempts": 0}),
    )

    payload = json.dumps({
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": amount,
        "request_id": request_id,
    })

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=payload,
        )
    except ReadTimeoutError:
        logger.error(
            "PaymentValidationTimeout",
            extra={
                "upstream_function": "payment-validation-service",
                "request_id": request_id,
                "order_id": order_id,
                "error_detail": "Lambda invoke timed out after 5 seconds",
                "endpoint": "POST /orders",
            },
        )
        raise RuntimeError("Payment validation failed")
    except (ClientError, Exception) as e:
        logger.error(
            "PaymentValidationError",
            extra={
                "upstream_function": "payment-validation-service",
                "request_id": request_id,
                "order_id": order_id,
                "error_detail": str(e),
                "endpoint": "POST /orders",
            },
        )
        raise RuntimeError("Payment validation failed") from e

    # Parse response payload
    try:
        response_payload = json.loads(response["Payload"].read())
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(
            "PaymentValidationError",
            extra={
                "upstream_function": "payment-validation-service",
                "request_id": request_id,
                "order_id": order_id,
                "error_detail": f"Invalid response payload: {e}",
                "endpoint": "POST /orders",
            },
        )
        raise RuntimeError("Payment validation failed") from e

    # Check for Lambda function error
    if "FunctionError" in response:
        logger.error(
            "PaymentValidationError",
            extra={
                "upstream_function": "payment-validation-service",
                "request_id": request_id,
                "order_id": order_id,
                "error_detail": response_payload.get("errorMessage", "Lambda function error"),
                "endpoint": "POST /orders",
            },
        )
        raise RuntimeError("Payment validation failed")

    # Check payment status
    status = response_payload.get("status")
    if status != "approved":
        error_detail = response_payload.get("error", f"Payment status: {status}")
        logger.error(
            "PaymentValidationError",
            extra={
                "upstream_function": "payment-validation-service",
                "request_id": request_id,
                "order_id": order_id,
                "error_detail": error_detail,
                "endpoint": "POST /orders",
            },
        )
        raise RuntimeError("Payment validation failed")

    return response_payload


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
    """Create a new order and store it in DynamoDB."""
    now = datetime.now(timezone.utc).isoformat()
    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    total_amount = round(payload.quantity * payload.unit_price, 2)
    request_id = _get_request_id()

    # Validate payment BEFORE persisting order to DynamoDB
    # If payment validation fails, RuntimeError is raised and order is NOT persisted
    _validate_payment(order_id, payload.customer_id, total_amount, request_id)

    item = {
        "order_id": order_id,
        "customer_id": payload.customer_id,
        "product_name": payload.product_name,
        "quantity": payload.quantity,
        "unit_price": Decimal(str(payload.unit_price)),
        "total_amount": Decimal(str(total_amount)),
        "status": "pending",
        "shipping_address": payload.shipping_address,
        "created_at": now,
        "updated_at": now,
    }

    try:
        table = _get_table()
        table.put_item(Item=item)
    except ClientError as e:
        logger.error("DynamoDB error creating order: %s", e, exc_info=True)
        raise RuntimeError("Failed to create order") from e

    logger.info("Order created: %s", order_id, extra={"endpoint": "POST /orders", "request_id": request_id})
    return _to_response({**item, "unit_price": float(item["unit_price"]), "total_amount": float(item["total_amount"])})


def get_order(order_id: str) -> OrderResponse | None:
    """Retrieve a single order by ID."""
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
    """List recent orders from DynamoDB."""
    try:
        table = _get_table()
        resp = table.scan(Limit=limit)
    except ClientError as e:
        logger.error("DynamoDB error listing orders: %s", e, exc_info=True)
        raise RuntimeError("Failed to list orders") from e

    items = resp.get("Items", [])
    return [_to_response(item) for item in items]
