# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""FastAPI application entry point for the order processing service."""

import logging
import uuid
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.logging_config import setup_logging
from app.routes.health import router as health_router
from app.routes.orders import router as orders_router

# Configure structured logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Order Processing Service", version="1.2.0")

# Enable CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(orders_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request for log correlation."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, log full stack trace, return 500."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception: %s",
        str(exc),
        exc_info=True,
        extra={"request_id": request_id, "endpoint": f"{request.method} {request.url.path}"},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )
