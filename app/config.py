# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Environment-based configuration for the order processing service."""

import os
import sys


class Config:
    """Application configuration loaded from environment variables."""

    DYNAMODB_TABLE_NAME: str
    AWS_REGION: str
    CONNECTION_POOL_SIZE: int
    SERVICE_NAME: str
    LOG_LEVEL: str

    def __init__(self) -> None:
        self.DYNAMODB_TABLE_NAME = self._require("DYNAMODB_TABLE_NAME")
        self.AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
        self.CONNECTION_POOL_SIZE = int(os.environ.get("CONNECTION_POOL_SIZE", "10"))
        self.SERVICE_NAME = os.environ.get("SERVICE_NAME", "order-processing-service")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    @staticmethod
    def _require(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            print(f"FATAL: Required environment variable '{name}' is not set.", file=sys.stderr)
            sys.exit(1)
        return value


config = Config() if os.environ.get("DYNAMODB_TABLE_NAME") else None


def get_config() -> Config:
    """Return the singleton config, creating it if needed."""
    global config
    if config is None:
        config = Config()
    return config
