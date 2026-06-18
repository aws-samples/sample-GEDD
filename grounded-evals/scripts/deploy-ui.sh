#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground UI to ECS ==="

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/agent-playground-ui"
SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="${SCRIPT_DIR}/.."

cd "$PROJECT_ROOT"

# Authenticate with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build container image
echo "Building Docker image..."
docker build -t agent-playground-ui .

# Tag and push
echo "Pushing to ECR..."
docker tag agent-playground-ui:latest "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

# Force new ECS deployment
echo "Triggering ECS deployment..."
aws ecs update-service \
    --cluster AgentPlayground-Ecs-AgentPlaygroundCluster* \
    --service AgentPlayground-Ecs-Service* \
    --force-new-deployment \
    --region "$REGION" \
    2>/dev/null || echo "Note: Update the cluster/service names if they differ"

echo ""
echo "=== UI deployment complete ==="
echo "The new container will be live in ~2 minutes"
echo "Check CloudFront URL:"
echo "aws cloudformation describe-stacks --stack-name AgentPlayground-Network --region ${REGION} --query 'Stacks[0].Outputs[?OutputKey==\`CloudFrontUrl\`].OutputValue' --output text"
