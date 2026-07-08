#!/bin/bash
# Inject Scenario B: Throttling — set Reserved Concurrency to 1, causing throttles under load
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="order-processing-service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Injecting Throttling Scenario ==="
echo "Setting Reserved Concurrency to 1 on Lambda function..."
echo "This means only 1 request can execute at a time — all others get throttled (429)."
echo ""

# Set reserved concurrency to 1
aws lambda put-function-concurrency \
  --function-name "$FUNCTION_NAME" \
  --reserved-concurrent-executions 1 \
  --region "$REGION" > /dev/null

echo "Reserved Concurrency set to 1."
echo ""

# Get the API URL
API_URL=$(aws cloudformation describe-stacks --stack-name devops-agent-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text --region "$REGION")

echo "Running load generator to trigger throttling..."
echo "Sending 10 concurrent requests for 20 seconds..."
echo ""
python3 "$SCRIPT_DIR/load_generator.py" --url "${API_URL}/orders" --concurrency 10 --duration 20

echo ""
echo "Throttling scenario injected."
echo "Check CloudWatch metrics for Throttles on $FUNCTION_NAME."
echo ""
echo "To trigger the webhook alert, run:"
echo "  python3 scripts/simulate_webhook.py --scenario throttling"
