# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Simulate a webhook alert to trigger DevOps Agent investigation.

Usage:
    python scripts/simulate_webhook.py --scenario code-bug
    python scripts/simulate_webhook.py --scenario infra-issue
"""

import argparse
import hashlib
import hmac
import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

if not WEBHOOK_URL or not WEBHOOK_SECRET:
    print("ERROR: WEBHOOK_URL and WEBHOOK_SECRET environment variables must be set.")
    print("  export WEBHOOK_URL='https://event-ai.us-east-1.api.aws/webhook/generic/<your-endpoint-id>'")
    print("  export WEBHOOK_SECRET='<your-hmac-secret>'")
    raise SystemExit(1)


SCENARIOS = {
    "code-bug": {
        "eventType": "incident",
        "action": "created",
        "priority": "HIGH",
        "title": "Order Processing Service - HTTP 500 errors on POST /orders",
        "description": (
            "CloudWatch alarm 'order-processing-error-rate-high' triggered. "
            "The order-processing-service Lambda function is returning HTTP 500 errors "
            "on POST /orders requests. GET endpoints (/health, /orders) are still functional. "
            "Error rate exceeded threshold of 5 errors per minute. "
            "Customers are unable to place new orders. "
            "Lambda function: order-processing-service, Region: us-east-1, "
            "Account: <your-aws-account-id>."
        ),
        "service": "order-processing-service",
        "data": {
            "metadata": {
                "region": "us-east-1",
                "environment": "production",
                "alarmName": "order-processing-error-rate-high",
                "functionName": "order-processing-service",
                "affectedEndpoint": "POST /orders",
            }
        },
    },
    "infra-issue": {
        "eventType": "incident",
        "action": "created",
        "priority": "HIGH",
        "title": "Order Processing Service - P99 latency exceeds 5 seconds",
        "description": (
            "CloudWatch alarm 'order-processing-latency-p99-high' triggered. "
            "The order-processing-service Lambda function p99 duration has exceeded "
            "5000ms threshold. Requests are timing out under load. "
            "This started after a configuration change to the function. "
            "Lambda function: order-processing-service, Region: us-east-1, "
            "Account: <your-aws-account-id>."
        ),
        "service": "order-processing-service",
        "data": {
            "metadata": {
                "region": "us-east-1",
                "environment": "production",
                "alarmName": "order-processing-latency-p99-high",
                "functionName": "order-processing-service",
                "affectedEndpoint": "POST /orders",
            }
        },
    },
    "throttling": {
        "eventType": "incident",
        "action": "created",
        "priority": "HIGH",
        "title": "Order Processing Service - Lambda throttling detected",
        "description": (
            "CloudWatch alarm triggered: Lambda function 'order-processing-service' is "
            "experiencing high throttle rate. Multiple requests are being rejected with "
            "HTTP 429 (Too Many Requests). The function's reserved concurrency appears "
            "to be misconfigured, causing requests to be throttled even under normal load. "
            "Customers are experiencing intermittent failures when placing orders. "
            "Lambda function: order-processing-service, Region: us-east-1, "
            "Account: <your-aws-account-id>."
        ),
        "service": "order-processing-service",
        "data": {
            "metadata": {
                "region": "us-east-1",
                "environment": "production",
                "alarmName": "order-processing-throttle-rate-high",
                "functionName": "order-processing-service",
                "affectedEndpoint": "ALL",
            }
        },
    },
    "cascading-failure": {
        "eventType": "incident",
        "action": "created",
        "priority": "HIGH",
        "title": "Order Processing Service - POST /orders timeouts under concurrent load",
        "description": (
            "CloudWatch alarm 'order-processing-upstream-timeout' triggered. "
            "The order-processing-service Lambda function is experiencing intermittent "
            "HTTP 503 errors and elevated latency on POST /orders requests under concurrent load. "
            "Single requests succeed but burst traffic causes widespread failures. "
            "GET endpoints (/health, /orders) remain responsive. "
            "Customers are reporting intermittent order placement failures. "
            "Lambda function: order-processing-service, Region: us-east-1, "
            "Account: <your-aws-account-id>."
        ),
        "service": "order-processing-service",
        "data": {
            "metadata": {
                "region": "us-east-1",
                "environment": "production",
                "alarmName": "order-processing-upstream-timeout",
                "functionName": "order-processing-service",
                "affectedEndpoint": "POST /orders",
            }
        },
    },
}


def send_webhook(scenario: str) -> None:
    """Send HMAC-signed webhook to DevOps Agent."""
    payload_data = SCENARIOS[scenario].copy()
    payload_data["incidentId"] = f"{scenario}-{int(time.time())}"
    payload_data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    payload = json.dumps(payload_data)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Generate HMAC-SHA256 signature
    message = f"{timestamp}:{payload}"
    signature = base64.b64encode(
        hmac.new(
            WEBHOOK_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-amzn-event-timestamp": timestamp,
        "x-amzn-event-signature": signature,
    }

    print(f"Sending webhook for scenario: {scenario}")
    print(f"URL: {WEBHOOK_URL}")
    print(f"Timestamp: {timestamp}")
    print(f"Payload:")
    print(json.dumps(payload_data, indent=2))
    print()

    req = Request(WEBHOOK_URL, data=payload.encode("utf-8"), headers=headers, method="POST")

    try:
        with urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            print(f"Response: HTTP {status}")
            print(f"Body: {body}")
            if status == 200:
                print("\nSUCCESS: Webhook received. Check DevOps Agent console for investigation.")
    except HTTPError as e:
        print(f"ERROR: HTTP {e.code}")
        print(f"Body: {e.read().decode('utf-8')}")
    except URLError as e:
        print(f"ERROR: {e.reason}")


def main():
    parser = argparse.ArgumentParser(description="Send webhook alert to DevOps Agent")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["code-bug", "infra-issue", "throttling", "cascading-failure"],
        help="Which alert scenario to trigger",
    )
    args = parser.parse_args()
    send_webhook(args.scenario)


if __name__ == "__main__":
    main()
