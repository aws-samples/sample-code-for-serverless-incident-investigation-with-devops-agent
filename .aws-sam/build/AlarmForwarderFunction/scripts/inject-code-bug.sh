#!/bin/bash
# Inject Scenario A: Code Bug — swap order_service.py with buggy variant causing KeyError on POST /orders
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="order-processing-service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Injecting Code Bug Scenario ==="
echo "Replacing order_service.py with buggy variant (KeyError on delivery_address)..."

# Backup the healthy file
cp "$APP_DIR/app/services/order_service.py" "$APP_DIR/app/services/order_service.py.healthy"

# Swap in the buggy version
cp "$APP_DIR/buggy/order_service.py" "$APP_DIR/app/services/order_service.py"

echo "Rebuilding and deploying with SAM..."
cd "$APP_DIR"
sam build --template-file infra/lambda-template.yaml
sam deploy --stack-name devops-agent-demo --resolve-s3 --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region "$REGION" --no-confirm-changeset

# Get the API URL
API_URL=$(aws cloudformation describe-stacks --stack-name devops-agent-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text --region "$REGION")

echo "Waiting for deployment to stabilize..."
sleep 5

echo "Confirming degradation..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"c1","product_name":"Widget","quantity":1,"unit_price":9.99,"shipping_address":"123 Main St"}')

if [ "$HTTP_CODE" = "500" ]; then
  echo "SUCCESS: POST /orders returns HTTP 500 — code bug injected."
  echo "GET /health and GET /orders still work (only writes are broken)."
else
  echo "WARNING: POST /orders returned HTTP ${HTTP_CODE} — expected 500."
fi

echo ""
echo "To trigger the webhook alert, run:"
echo "  python3 scripts/simulate_webhook.py --scenario code-bug --url <DEVOPS_AGENT_WEBHOOK_URL>"
