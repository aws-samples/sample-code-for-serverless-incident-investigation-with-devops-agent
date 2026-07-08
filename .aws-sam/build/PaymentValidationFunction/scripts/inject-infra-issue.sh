#!/bin/bash
# Inject Scenario B: Infrastructure Issue — set CONNECTION_POOL_SIZE=1 causing pool exhaustion under load
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="order-processing-service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Injecting Infrastructure Issue Scenario ==="
echo "Setting CONNECTION_POOL_SIZE=1 on Lambda function..."

# Update the Lambda environment variable directly (no redeploy needed)
CURRENT_ENV=$(aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --query 'Environment.Variables' --output json)

NEW_ENV=$(echo "$CURRENT_ENV" | jq '.CONNECTION_POOL_SIZE = "1"')

aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --environment "{\"Variables\": $NEW_ENV}" > /dev/null

echo "Waiting for function update to complete..."
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

# Get the API URL
API_URL=$(aws cloudformation describe-stacks --stack-name devops-agent-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text --region "$REGION")

echo "Running load generator to trigger pool exhaustion..."
python3 "$SCRIPT_DIR/load_generator.py" --url "${API_URL}/orders" --concurrency 10 --duration 30

echo ""
echo "Infrastructure issue injected. Check CloudWatch for latency alarm."
echo ""
echo "To trigger the webhook alert, run:"
echo "  python3 scripts/simulate_webhook.py --scenario infra-issue --url <DEVOPS_AGENT_WEBHOOK_URL>"
