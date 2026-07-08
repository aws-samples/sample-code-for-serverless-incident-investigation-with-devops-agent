#!/bin/bash
# Setup script for the DevOps Agent demo
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="devops-agent-demo"

echo "=== DevOps Agent Demo Setup ==="

# Check prerequisites
echo "Checking prerequisites..."
command -v aws >/dev/null 2>&1 || { echo "ERROR: AWS CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not found. Install: https://docs.docker.com/get-docker/"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 not found. Install Python 3.12+"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found. Install: brew install jq"; exit 1; }

# Validate AWS credentials
aws sts get-caller-identity --region "$REGION" > /dev/null || { echo "ERROR: AWS credentials not configured"; exit 1; }
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/order-processing-service"

echo "Account: $ACCOUNT_ID, Region: $REGION"

# Validate resource naming
echo "Validating resource naming..."
python3 scripts/validate_naming.py

# Deploy infrastructure
echo "Deploying CloudFormation stack..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region "$REGION")
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region "$REGION" | tr '\t' ',')

aws cloudformation deploy \
  --template-file infra/template.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides VpcId="$VPC_ID" SubnetIds="$SUBNET_IDS" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

# Build and push Docker images
echo "Building and pushing Docker images..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

docker build -t order-processing-service:v1.2.0 -f Dockerfile .
docker tag order-processing-service:v1.2.0 "${ECR_URI}:v1.2.0"
docker push "${ECR_URI}:v1.2.0"

docker build -t order-processing-service:v1.2.1-buggy -f Dockerfile.buggy .
docker tag order-processing-service:v1.2.1-buggy "${ECR_URI}:v1.2.1-buggy"
docker push "${ECR_URI}:v1.2.1-buggy"

# Seed sample data
echo "Seeding sample data..."
python3 scripts/seed_data.py

# Verify health
ALB_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' --output text --region "$REGION")
echo "Waiting for service to stabilize..."
sleep 30

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${ALB_URL}/health" || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "SUCCESS: Health check passed."
else
  echo "WARNING: Health check returned HTTP ${HTTP_CODE}. Service may still be starting."
fi

echo ""
echo "=== Setup Complete ==="
echo "ALB URL: $ALB_URL"
echo "ECR URI: $ECR_URI"
echo "Stack:   $STACK_NAME"
