# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Lambda handler that wraps the FastAPI app using Mangum."""

from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
