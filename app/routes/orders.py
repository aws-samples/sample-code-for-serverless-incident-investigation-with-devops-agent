# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Order CRUD endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from app.models.order import OrderCreate, OrderResponse
from app.services import order_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders():
    """List recent orders."""
    try:
        return order_service.list_orders()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Retrieve a specific order."""
    try:
        order = order_service.get_order(order_id)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(payload: OrderCreate):
    """Create a new order."""
    try:
        return order_service.create_order(payload)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
