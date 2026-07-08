#!/bin/bash
# Reset the demo environment to healthy baseline
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="order-processing-service"
PAYMENT_TABLE="payment-records"
API_URL="https://rut1bpvz79.execute-api.us-east-1.amazonaws.com"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Resetting Demo Environment ==="

# Restore healthy order_service.py if backup exists
if [ -f "$APP_DIR/app/services/order_service.py.healthy" ]; then
  echo "Restoring healthy order_service.py..."
  cp "$APP_DIR/app/services/order_service.py.healthy" "$APP_DIR/app/services/order_service.py"
  rm "$APP_DIR/app/services/order_service.py.healthy"

  echo "Rebuilding and deploying healthy code..."
  cd "$APP_DIR"
  sam build --template-file infra/lambda-template.yaml
  sam deploy --stack-name devops-agent-demo --resolve-s3 --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region "$REGION" --no-confirm-changeset
else
  echo "No code bug backup found — code is already healthy."
fi

# Remove reserved concurrency (if set)
echo "Removing reserved concurrency limit..."
aws lambda delete-function-concurrency \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" 2>/dev/null || true

# Reset CONNECTION_POOL_SIZE to 10
echo "Resetting CONNECTION_POOL_SIZE to 10..."
CURRENT_ENV=$(aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --query 'Environment.Variables' --output json)

NEW_ENV=$(echo "$CURRENT_ENV" | jq '.CONNECTION_POOL_SIZE = "10"')

aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --environment "{\"Variables\": $NEW_ENV}" > /dev/null

echo "Waiting for function update to complete..."
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

# Restore payment-records DynamoDB table capacity to 5 RCU / 5 WCU
echo "Restoring $PAYMENT_TABLE capacity to 5 RCU / 5 WCU..."
if ! aws dynamodb update-table \
  --table-name "$PAYMENT_TABLE" \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region "$REGION" > /dev/null 2>&1; then
  echo "ERROR: Failed to restore $PAYMENT_TABLE capacity."
  exit 1
fi

echo "Waiting for $PAYMENT_TABLE to reach ACTIVE status..."
if ! aws dynamodb wait table-exists --table-name "$PAYMENT_TABLE" --region "$REGION" 2>/dev/null; then
  echo "ERROR: Timed out waiting for $PAYMENT_TABLE to reach ACTIVE status."
  exit 1
fi
echo "$PAYMENT_TABLE capacity restored to 5 RCU / 5 WCU."

# Verify POST /orders returns HTTP 201 within 10 seconds
echo "Verifying POST /orders returns HTTP 201..."
VERIFY_PAYLOAD='{"customer_id": "cust-reset-check", "items": [{"name": "Reset Verification", "price": 1.00, "quantity": 1}]}'
DEADLINE=$((SECONDS + 10))
VERIFIED=false

while [ $SECONDS -lt $DEADLINE ]; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_URL}/orders" \
    -H "Content-Type: application/json" \
    -d "$VERIFY_PAYLOAD" --max-time 5 || echo "000")
  if [ "$HTTP_CODE" = "201" ]; then
    VERIFIED=true
    break
  fi
  sleep 1
done

if [ "$VERIFIED" = true ]; then
  echo "SUCCESS: Demo environment reset to healthy baseline. POST /orders returned HTTP 201."
else
  echo "ERROR: POST /orders did not return HTTP 201 within 10 seconds (last response: HTTP ${HTTP_CODE}). Service did not recover."
  exit 1
fi
