#!/bin/bash
# Inject Scenario C: Cascading Failure — reduce payment-records DynamoDB capacity to trigger throttling
# that cascades as errors in the order-processing-service.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
TABLE_NAME="payment-records"
API_URL="https://rut1bpvz79.execute-api.us-east-1.amazonaws.com"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Injecting Cascading Failure Scenario ==="
echo "Reducing $TABLE_NAME DynamoDB table capacity to 1 RCU / 1 WCU..."
echo "This will cause ProvisionedThroughputExceededException on the payment-validation-service,"
echo "which cascades as HTTP 500 errors on the order-processing-service POST /orders endpoint."
echo ""

# Reduce payment-records table capacity to 1 RCU / 1 WCU
if ! aws dynamodb update-table \
  --table-name "$TABLE_NAME" \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 \
  --region "$REGION" > /dev/null 2>&1; then
  echo "ERROR: Failed to update $TABLE_NAME capacity. Check that the table exists and you have permissions."
  exit 1
fi

echo "Capacity update submitted. Waiting for table to reach ACTIVE status..."

# Wait for table to reach ACTIVE status
if ! aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION" 2>/dev/null; then
  echo "ERROR: Timed out waiting for $TABLE_NAME to reach ACTIVE status."
  exit 1
fi

echo "$TABLE_NAME capacity reduced to 1 RCU / 1 WCU."
echo ""

# Run load generator to trigger throttling
echo "Running load generator to trigger cascading failure..."
echo "Sending 10 concurrent requests for 20 seconds to POST /orders..."
echo ""
python3 "$SCRIPT_DIR/load_generator.py" --url "${API_URL}/orders" --concurrency 10 --duration 20

echo ""
echo "=== Cascading Failure Scenario Active ==="
echo "The payment-records-throttle-alarm is expected to trigger within 1-2 minutes."
echo "The order-processing-service will return HTTP 500 errors on POST /orders."
echo ""
echo "To trigger the webhook alert, run:"
echo "  python3 demo-app/scripts/simulate_webhook.py --scenario cascading-failure"
echo ""
echo "To reset, run:"
echo "  bash demo-app/scripts/reset.sh"
