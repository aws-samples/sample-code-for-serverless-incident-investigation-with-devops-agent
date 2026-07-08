# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Seed DynamoDB with sample order data for the demo."""

import boto3
from decimal import Decimal

REGION = "us-east-1"
TABLE_NAME = "order-records"

SAMPLE_ORDERS = [
    {"order_id": "ord-a1b2c3d4", "customer_id": "cust-001", "product_name": "Wireless Headphones", "quantity": 2, "unit_price": Decimal("49.99"), "total_amount": Decimal("99.98"), "status": "confirmed", "shipping_address": "742 Evergreen Terrace, Springfield", "created_at": "2024-01-14T10:00:00Z", "updated_at": "2024-01-14T10:05:00Z"},
    {"order_id": "ord-e5f6g7h8", "customer_id": "cust-002", "product_name": "USB-C Hub", "quantity": 1, "unit_price": Decimal("34.99"), "total_amount": Decimal("34.99"), "status": "shipped", "shipping_address": "1600 Pennsylvania Ave, Washington DC", "created_at": "2024-01-13T14:30:00Z", "updated_at": "2024-01-14T08:00:00Z"},
    {"order_id": "ord-i9j0k1l2", "customer_id": "cust-003", "product_name": "Mechanical Keyboard", "quantity": 1, "unit_price": Decimal("129.00"), "total_amount": Decimal("129.00"), "status": "pending", "shipping_address": "221B Baker Street, London", "created_at": "2024-01-15T09:15:00Z", "updated_at": "2024-01-15T09:15:00Z"},
    {"order_id": "ord-m3n4o5p6", "customer_id": "cust-001", "product_name": "Monitor Stand", "quantity": 1, "unit_price": Decimal("59.99"), "total_amount": Decimal("59.99"), "status": "delivered", "shipping_address": "742 Evergreen Terrace, Springfield", "created_at": "2024-01-10T16:00:00Z", "updated_at": "2024-01-12T11:30:00Z"},
    {"order_id": "ord-q7r8s9t0", "customer_id": "cust-004", "product_name": "Laptop Sleeve", "quantity": 3, "unit_price": Decimal("24.99"), "total_amount": Decimal("74.97"), "status": "confirmed", "shipping_address": "350 Fifth Avenue, New York", "created_at": "2024-01-15T11:00:00Z", "updated_at": "2024-01-15T11:02:00Z"},
]


def main():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    with table.batch_writer() as batch:
        for order in SAMPLE_ORDERS:
            batch.put_item(Item=order)

    print(f"Seeded {len(SAMPLE_ORDERS)} orders into {TABLE_NAME}")


if __name__ == "__main__":
    main()
