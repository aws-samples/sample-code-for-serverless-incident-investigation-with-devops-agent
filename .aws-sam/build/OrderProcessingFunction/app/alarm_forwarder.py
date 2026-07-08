"""Lambda handler that forwards CloudWatch Alarm SNS notifications to DevOps Agent webhook.

This function receives SNS messages from CloudWatch Alarms, transforms them into
the DevOps Agent webhook format, signs the payload with HMAC-SHA256, and POSTs
to the DevOps Agent endpoint.

Environment Variables:
    WEBHOOK_URL: The DevOps Agent webhook endpoint URL
    WEBHOOK_SECRET: The HMAC-SHA256 signing secret (base64 encoded)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# Map alarm names to alert scenarios
ALARM_SCENARIOS = {
    "order-processing-error-rate-high": {
        "title": "Order Processing Service - Elevated error rate and timeouts on POST /orders",
        "description": (
            "CloudWatch alarm 'order-processing-error-rate-high' triggered. "
            "The order-processing-service Lambda function is returning elevated HTTP 500 "
            "errors and experiencing timeouts on POST /orders requests. "
            "Error rate has exceeded threshold of 5 errors per minute. "
            "GET endpoints (/health, /orders) remain responsive. "
            "Customers are unable to place new orders. "
            "Lambda function: order-processing-service, Region: {region}, "
            "Account: {account}."
        ),
        "service": "order-processing-service",
        "priority": "HIGH",
        "metadata": {
            "alarmName": "order-processing-error-rate-high",
            "functionName": "order-processing-service",
            "affectedEndpoint": "POST /orders",
        },
    },
    "order-processing-latency-p99-high": {
        "title": "Order Processing Service - P99 latency exceeds 5 seconds",
        "description": (
            "CloudWatch alarm 'order-processing-latency-p99-high' triggered. "
            "The order-processing-service Lambda function p99 duration has exceeded "
            "5000ms threshold. Requests are timing out under load. "
            "Lambda function: order-processing-service, Region: {region}, "
            "Account: {account}."
        ),
        "service": "order-processing-service",
        "priority": "HIGH",
        "metadata": {
            "alarmName": "order-processing-latency-p99-high",
            "functionName": "order-processing-service",
            "affectedEndpoint": "POST /orders",
        },
    },
    "payment-records-throttle-alarm": {
        "title": "Order Processing Service - Elevated error rate and timeouts on POST /orders",
        "description": (
            "CloudWatch alarm 'order-processing-error-rate-high' triggered. "
            "The order-processing-service Lambda function is returning elevated HTTP 500 "
            "errors and experiencing timeouts on POST /orders requests. "
            "Error rate has exceeded threshold of 5 errors per minute. "
            "GET endpoints (/health, /orders) remain responsive. "
            "Customers are unable to place new orders. "
            "Lambda function: order-processing-service, Region: {region}, "
            "Account: {account}."
        ),
        "service": "order-processing-service",
        "priority": "HIGH",
        "metadata": {
            "alarmName": "order-processing-error-rate-high",
            "functionName": "order-processing-service",
            "affectedEndpoint": "POST /orders",
        },
    },
}


def _sign_payload(payload: str, timestamp: str) -> str:
    """Generate HMAC-SHA256 signature for the webhook payload."""
    message = f"{timestamp}:{payload}"
    signature = base64.b64encode(
        hmac.new(
            WEBHOOK_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    return signature


def _send_webhook(payload_data: dict) -> dict:
    """Send signed webhook to DevOps Agent."""
    payload = json.dumps(payload_data)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    signature = _sign_payload(payload, timestamp)

    headers = {
        "Content-Type": "application/json",
        "x-amzn-event-timestamp": timestamp,
        "x-amzn-event-signature": signature,
    }

    req = Request(WEBHOOK_URL, data=payload.encode("utf-8"), headers=headers, method="POST")

    try:
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            logger.info("Webhook sent successfully: HTTP %d", status)
            return {"statusCode": status, "body": body}
    except HTTPError as e:
        logger.error("Webhook HTTP error: %d - %s", e.code, e.read().decode("utf-8"))
        return {"statusCode": e.code, "error": str(e)}
    except URLError as e:
        logger.error("Webhook URL error: %s", e.reason)
        return {"statusCode": 500, "error": str(e.reason)}


def handler(event, context):
    """
    Lambda handler for SNS → DevOps Agent webhook forwarding.

    Receives CloudWatch Alarm notifications via SNS, transforms them into
    the DevOps Agent webhook format, and forwards them.
    """
    if not WEBHOOK_URL or not WEBHOOK_SECRET:
        logger.error("WEBHOOK_URL or WEBHOOK_SECRET not configured")
        return {"statusCode": 500, "error": "Missing configuration"}

    results = []

    for record in event.get("Records", []):
        sns_message = record.get("Sns", {})
        message_body = sns_message.get("Message", "{}")

        try:
            alarm_data = json.loads(message_body)
        except json.JSONDecodeError:
            logger.error("Failed to parse SNS message: %s", message_body)
            continue

        alarm_name = alarm_data.get("AlarmName", "")
        new_state = alarm_data.get("NewStateValue", "")
        region = alarm_data.get("Region", "us-east-1")
        account = alarm_data.get("AWSAccountId", "")

        # Only forward ALARM state transitions (not OK or INSUFFICIENT_DATA)
        if new_state != "ALARM":
            logger.info("Skipping non-ALARM state: %s for %s", new_state, alarm_name)
            continue

        # Look up the scenario for this alarm
        scenario = ALARM_SCENARIOS.get(alarm_name)
        if not scenario:
            logger.warning("No scenario mapping for alarm: %s", alarm_name)
            continue

        # Build the webhook payload
        payload_data = {
            "eventType": "incident",
            "action": "created",
            "priority": scenario["priority"],
            "title": scenario["title"],
            "description": scenario["description"].format(region=region, account=account),
            "service": scenario["service"],
            "incidentId": f"{alarm_name}-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "data": {
                "metadata": {
                    "region": region,
                    "environment": "production",
                    **scenario["metadata"],
                }
            },
        }

        logger.info("Forwarding alarm '%s' to DevOps Agent as incident", alarm_name)
        result = _send_webhook(payload_data)
        results.append({"alarm": alarm_name, "result": result})

    return {"statusCode": 200, "forwarded": len(results), "results": results}
