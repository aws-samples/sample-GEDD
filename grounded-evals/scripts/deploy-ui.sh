#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground UI to ECS ==="

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/agent-playground-ui"
SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="${SCRIPT_DIR}/.."
CLUSTER_NAME=$(
    aws ecs list-clusters --region "$REGION" \
        --query "clusterArns[?contains(@, 'AgentPlayground-Ecs-Cluster')]" \
        --output text | awk -F/ 'NR==1 {print $2}'
)

if [[ -z "${CLUSTER_NAME}" ]]; then
    echo "Unable to resolve Agent Playground ECS cluster name" >&2
    exit 1
fi

SERVICE_NAME=$(
    aws ecs list-services --cluster "$CLUSTER_NAME" --region "$REGION" \
        --query "serviceArns[?contains(@, 'AgentPlayground-Ecs-Service')]" \
        --output text | awk -F/ 'NR==1 {print $3}'
)

if [[ -z "${SERVICE_NAME}" ]]; then
    echo "Unable to resolve Agent Playground ECS service name" >&2
    exit 1
fi

cd "$PROJECT_ROOT"

# Authenticate with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build and push an amd64 image so ECS/Fargate can pull it reliably.
echo "Building and pushing linux/amd64 Docker image..."
docker buildx build \
    --platform linux/amd64 \
    --provenance=false \
    --sbom=false \
    --tag "${ECR_URI}:latest" \
    --push \
    .

# Force new ECS deployment
echo "Triggering ECS deployment for ${CLUSTER_NAME}/${SERVICE_NAME}..."
aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE_NAME" \
    --force-new-deployment \
    --region "$REGION"

echo "Waiting for ECS service to stabilize..."
aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$REGION"

echo ""
echo "=== UI deployment complete ==="
echo "The new container is live"
echo "Check CloudFront URL:"
echo "aws cloudformation describe-stacks --stack-name AgentPlayground-Network --region ${REGION} --query 'Stacks[0].Outputs[?OutputKey==\`CloudFrontUrl\`].OutputValue' --output text"
