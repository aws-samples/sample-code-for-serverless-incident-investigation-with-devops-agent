# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Order Pydantic models for request/response validation."""

from pydantic import BaseModel


class OrderCreate(BaseModel):
    """Request body for creating a new order."""
    customer_id: str
    product_name: str
    quantity: int
    unit_price: float
    shipping_address: str


class OrderResponse(BaseModel):
    """Response body for order data."""
    order_id: str
    customer_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_amount: float
    status: str
    shipping_address: str
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    """Response body for health check."""
    status: str
    service: str
    version: str
