#!/bin/bash
# Reset the demo environment to healthy baseline
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="order-processing-service"
PAYMENT_TABLE="payment-records"
API_URL="${API_URL:-https://<your-api-id>.execute-api.us-east-1.amazonaws.com}"
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
CURRENT_CAP=$(aws dynamodb describe-table --table-name "$PAYMENT_TABLE" --region "$REGION" \
  --query 'Table.ProvisionedThroughput.ReadCapacityUnits' --output text 2>/dev/null || echo "5")
if [ "$CURRENT_CAP" != "5" ]; then
  if ! aws dynamodb update-table \
    --table-name "$PAYMENT_TABLE" \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region "$REGION" > /dev/null 2>&1; then
    echo "WARNING: Failed to restore $PAYMENT_TABLE capacity (may already be at 5/5)."
  else
    echo "Waiting for $PAYMENT_TABLE to reach ACTIVE status..."
    aws dynamodb wait table-exists --table-name "$PAYMENT_TABLE" --region "$REGION" 2>/dev/null || true
  fi
else
  echo "$PAYMENT_TABLE already at 5 RCU / 5 WCU."
fi
echo "$PAYMENT_TABLE capacity restored."

# Restore payment-validation-service configuration
echo "Restoring payment-validation-service configuration..."
PAYMENT_FUNCTION="payment-validation-service"

# Restore timeout to 30 seconds
aws lambda update-function-configuration \
  --function-name "$PAYMENT_FUNCTION" \
  --timeout 30 \
  --region "$REGION" > /dev/null 2>&1 || true

# Remove reserved concurrency limit
aws lambda delete-function-concurrency \
  --function-name "$PAYMENT_FUNCTION" \
  --region "$REGION" 2>/dev/null || true

# Restore table name if it was changed
PV_ENV=$(aws lambda get-function-configuration \
  --function-name "$PAYMENT_FUNCTION" \
  --region "$REGION" \
  --query 'Environment.Variables' --output json 2>/dev/null || echo '{}')

if echo "$PV_ENV" | grep -q "DISABLED"; then
  PV_NEW_ENV=$(echo "$PV_ENV" | python3 -c "import sys,json; d=json.load(sys.stdin); d['PAYMENT_TABLE_NAME']='payment-records'; print(json.dumps(d))")
  aws lambda update-function-configuration \
    --function-name "$PAYMENT_FUNCTION" \
    --region "$REGION" \
    --environment "{\"Variables\": $PV_NEW_ENV}" > /dev/null
fi

aws lambda wait function-updated --function-name "$PAYMENT_FUNCTION" --region "$REGION"
echo "payment-validation-service restored (timeout=30s, concurrency=unreserved)."
echo "$PAYMENT_TABLE capacity restored to 5 RCU / 5 WCU."

# Verify POST /orders returns HTTP 201 within 10 seconds
echo "Verifying POST /orders returns HTTP 201..."
VERIFY_PAYLOAD='{"customer_id": "cust-reset-check", "product_name": "Reset Verification", "quantity": 1, "unit_price": 1.00, "shipping_address": "123 Reset St"}'
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
