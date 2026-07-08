#!/bin/bash
# Inject Scenario C: Cascading Failure — reduce payment-validation-service timeout and concurrency
# simulating a cost optimization that breaks the upstream service under load,
# cascading errors to the order service.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PAYMENT_FUNCTION="payment-validation-service"
API_URL="${API_URL:-https://<your-api-id>.execute-api.us-east-1.amazonaws.com}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Injecting Cascading Failure Scenario ==="
echo ""
echo "Scenario: The platform team reduced the $PAYMENT_FUNCTION Lambda"
echo "concurrency to 1 and timeout to 2s as part of a cost optimization."
echo "Single requests still work, but under any concurrent load the payment"
echo "service can only handle one request at a time — all others get throttled"
echo "or time out, cascading as HTTP 500 errors on POST /orders."
echo ""

# Step 1: Reduce payment-validation-service timeout to 2 seconds
echo "Reducing $PAYMENT_FUNCTION timeout to 2 seconds..."
if ! aws lambda update-function-configuration \
  --function-name "$PAYMENT_FUNCTION" \
  --timeout 2 \
  --region "$REGION" > /dev/null 2>&1; then
  echo "ERROR: Failed to update $PAYMENT_FUNCTION timeout."
  exit 1
fi
aws lambda wait function-updated --function-name "$PAYMENT_FUNCTION" --region "$REGION"

# Step 2: Set reserved concurrency to 1
echo "Setting $PAYMENT_FUNCTION reserved concurrency to 1..."
if ! aws lambda put-function-concurrency \
  --function-name "$PAYMENT_FUNCTION" \
  --reserved-concurrent-executions 1 \
  --region "$REGION" > /dev/null 2>&1; then
  echo "ERROR: Failed to set $PAYMENT_FUNCTION concurrency."
  exit 1
fi

echo "$PAYMENT_FUNCTION configured: timeout=2s, concurrency=1"
echo ""

# Step 3: Run load generator to trigger error rate alarm
echo "Running load generator to trigger cascading failure..."
echo "Sending 10 concurrent requests for 120 seconds to POST /orders..."
echo "(This ensures the CloudWatch alarm has sustained errors to evaluate)"
echo ""
python3 "$SCRIPT_DIR/load_generator.py" --url "${API_URL}/orders" --concurrency 10 --duration 120 &
LOAD_PID=$!

echo ""
echo "=== Cascading Failure Scenario Active ==="
echo "Load generator running in background (PID: $LOAD_PID)"
echo "The order-processing-error-rate-high alarm should trigger within 1-2 minutes."
echo "The DevOps Agent will be triggered automatically via SNS → webhook forwarder."
echo ""
echo "Behavior:"
echo "  - Single requests: PASS (one at a time gets through)"
echo "  - Burst/concurrent requests: MOSTLY FAIL (only 1 succeeds, rest timeout)"
echo "  - Health check: PASS (GET /health is unaffected)"
echo ""
echo "To stop the load generator: kill $LOAD_PID"
echo "To reset: bash demo-app/scripts/reset.sh"
