"""Unit tests for payment_handler.py."""

import io
import json
import logging
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(autouse=True)
def _env_vars(monkeypatch):
    """Set required environment variables for the handler."""
    monkeypatch.setenv("PAYMENT_TABLE_NAME", "payment-records")
    monkeypatch.setenv("SERVICE_NAME", "payment-validation-service")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id-123"
    return ctx


@pytest.fixture
def valid_event():
    return {
        "order_id": "ord-abc12345",
        "customer_id": "cust-xyz789",
        "amount": 49.99,
        "request_id": "req-correlation-001",
    }


class TestPaymentHandlerHappyPath:
    """Tests for successful payment validation."""

    @patch("app.payment_handler._get_table")
    def test_returns_approved_status(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        result = handler(valid_event, mock_context)

        assert result["status"] == "approved"
        assert result["request_id"] == "req-correlation-001"
        assert result["payment_id"].startswith("pay-")
        assert len(result["payment_id"]) == 12  # "pay-" + 8 hex chars

    @patch("app.payment_handler._get_table")
    def test_writes_payment_record_to_dynamodb(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        handler(valid_event, mock_context)

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]["Item"]
        assert item["order_id"] == "ord-abc12345"
        assert item["customer_id"] == "cust-xyz789"
        assert item["amount"] == 49.99
        assert item["status"] == "approved"
        assert item["payment_id"].startswith("pay-")
        assert "validated_at" in item

    @patch("app.payment_handler._get_table")
    def test_echoes_request_id_from_event(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        result = handler(valid_event, mock_context)

        assert result["request_id"] == valid_event["request_id"]


class TestPaymentHandlerThrottling:
    """Tests for ProvisionedThroughputExceededException handling."""

    @patch("app.payment_handler._get_table")
    def test_returns_error_on_throttle(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Rate exceeded"}},
            "PutItem",
        )
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        result = handler(valid_event, mock_context)

        assert result["status"] == "error"
        assert result["error"] == "ProvisionedThroughputExceededException"
        assert result["request_id"] == "req-correlation-001"

    @patch("app.payment_handler._get_table")
    def test_logs_structured_error_on_throttle(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Rate exceeded"}},
            "PutItem",
        )
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler, logger

        # Capture log output via a stream handler
        log_stream = io.StringIO()
        stream_handler = logging.StreamHandler(log_stream)
        from app.payment_handler import _JSONFormatter

        stream_handler.setFormatter(_JSONFormatter())
        logger.addHandler(stream_handler)

        try:
            handler(valid_event, mock_context)
            log_output = log_stream.getvalue().strip()
            log_entry = json.loads(log_output)
            assert log_entry["level"] == "ERROR"
            assert "ProvisionedThroughputExceededException" in log_entry["message"]
            assert log_entry["request_id"] == "req-correlation-001"
            assert log_entry["table"] == "payment-records"
            assert log_entry["operation"] == "PutItem"
        finally:
            logger.removeHandler(stream_handler)


class TestPaymentHandlerOtherErrors:
    """Tests for other DynamoDB errors."""

    @patch("app.payment_handler._get_table")
    def test_returns_error_on_other_client_error(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid item"}},
            "PutItem",
        )
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        result = handler(valid_event, mock_context)

        assert result["status"] == "error"
        assert result["request_id"] == "req-correlation-001"

    @patch("app.payment_handler._get_table")
    def test_returns_error_on_unexpected_exception(self, mock_get_table, valid_event, mock_context):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = RuntimeError("Something went wrong")
        mock_get_table.return_value = mock_table

        from app.payment_handler import handler

        result = handler(valid_event, mock_context)

        assert result["status"] == "error"
        assert "Something went wrong" in result["error"]
        assert result["request_id"] == "req-correlation-001"
