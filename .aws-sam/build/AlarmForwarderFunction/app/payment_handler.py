"""Lambda handler for payment-validation-service.

Validates payment for an order by writing a payment record to the
payment-records DynamoDB table. Returns approval status with a
payment_id for cross-service correlation.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# --- Structured JSON logging setup ---

TABLE_NAME = os.environ.get("PAYMENT_TABLE_NAME", "payment-records")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "payment-validation-service")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        # Merge any extra structured fields
        for key in ("request_id", "payment_id", "table", "operation", "order_id", "error_detail"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        if record.exc_info and record.exc_info[1]:
            entry["traceback"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def _setup_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    logger = logging.getLogger("payment_handler")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False
    return logger


logger = _setup_logging()


def _get_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(TABLE_NAME)


def handler(event, context):
    """
    Validate payment for an order.

    Input event:
        {
            "order_id": "ord-xxx",
            "customer_id": "cust-xxx",
            "amount": 49.99,
            "request_id": "<lambda-request-id>"
        }

    Output:
        {
            "status": "approved" | "error",
            "payment_id": "pay-xxx",
            "request_id": "<same-request-id>",
            "error": "<error message if status=error>"
        }
    """
    request_id = event.get("request_id", getattr(context, "aws_request_id", "unknown"))
    order_id = event.get("order_id", "unknown")
    customer_id = event.get("customer_id", "unknown")
    amount = event.get("amount", 0)

    payment_id = f"pay-{uuid.uuid4().hex[:8]}"
    validated_at = datetime.now(timezone.utc).isoformat()

    item = {
        "payment_id": payment_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": Decimal(str(amount)),
        "status": "approved",
        "validated_at": validated_at,
    }

    try:
        table = _get_table()
        table.put_item(Item=item)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ProvisionedThroughputExceededException":
            logger.error(
                "ProvisionedThroughputExceededException",
                extra={
                    "request_id": request_id,
                    "payment_id": payment_id,
                    "table": TABLE_NAME,
                    "operation": "PutItem",
                    "order_id": order_id,
                },
            )
            return {
                "status": "error",
                "error": "ProvisionedThroughputExceededException",
                "request_id": request_id,
            }
        # Other DynamoDB errors
        logger.error(
            "DynamoDB ClientError: %s",
            str(e),
            extra={
                "request_id": request_id,
                "payment_id": payment_id,
                "table": TABLE_NAME,
                "operation": "PutItem",
                "order_id": order_id,
                "error_detail": error_code,
            },
        )
        return {
            "status": "error",
            "error": str(e),
            "request_id": request_id,
        }
    except Exception as e:
        logger.error(
            "Unexpected error: %s",
            str(e),
            exc_info=True,
            extra={
                "request_id": request_id,
                "payment_id": payment_id,
                "table": TABLE_NAME,
                "operation": "PutItem",
                "order_id": order_id,
            },
        )
        return {
            "status": "error",
            "error": str(e),
            "request_id": request_id,
        }

    logger.info(
        "Payment approved",
        extra={
            "request_id": request_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "table": TABLE_NAME,
            "operation": "PutItem",
        },
    )

    return {
        "status": "approved",
        "payment_id": payment_id,
        "request_id": request_id,
    }
