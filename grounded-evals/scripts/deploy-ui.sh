#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground UI to ECS ==="

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/agent-playground-ui"
PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
ECS_STACK="${ECS_STACK:-AgentPlayground-Ecs}"
stack_output() {
    aws cloudformation describe-stacks --stack-name "$ECS_STACK" --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
ECS_CLUSTER="${ECS_CLUSTER:-$(stack_output ClusterName)}"
ECS_SERVICE="${ECS_SERVICE:-$(stack_output ServiceName)}"
if [[ -z "$ECS_CLUSTER" || "$ECS_CLUSTER" == "None" || -z "$ECS_SERVICE" || "$ECS_SERVICE" == "None" ]]; then
    echo "Could not read ClusterName/ServiceName outputs from stack $ECS_STACK in $REGION." >&2
    echo "Deploy the infrastructure first (scripts/deploy-infra.sh) or set ECS_CLUSTER and ECS_SERVICE." >&2
    exit 1
fi
GIT_SHA="$(git -C "$(dirname "$0")" rev-parse --short HEAD 2>/dev/null || echo manual)"
SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="${SCRIPT_DIR}/.."

cd "$PROJECT_ROOT"

# Authenticate with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build and push container image. Fargate runs linux/amd64, while local dev
# machines may default to arm64.
echo "Building and pushing Docker image for ${PLATFORM}..."
docker buildx build --platform "$PLATFORM" -t "${ECR_URI}:latest" -t "${ECR_URI}:${GIT_SHA}" --push .

# Force new ECS deployment
echo "Triggering ECS deployment..."
aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --force-new-deployment \
    --region "$REGION" \
    >/dev/null

echo ""
echo "=== UI deployment complete ==="
echo "The new container will be live in ~2 minutes"
echo "Check CloudFront URL:"
echo "aws cloudformation describe-stacks --stack-name AgentPlayground-Network --region ${REGION} --query 'Stacks[0].Outputs[?OutputKey==\`CloudFrontUrl\`].OutputValue' --output text"
