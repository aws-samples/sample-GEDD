#!/bin/bash
set -euo pipefail

echo "=== Full Deployment: Agent Playground ==="
echo ""

SCRIPT_DIR="$(dirname "$0")"

echo "Step 1/3: Infrastructure (CDK)"
echo "==============================="
bash "${SCRIPT_DIR}/deploy-infra.sh"
echo ""

echo "Step 2/3: AgentCore Agent"
echo "========================="
bash "${SCRIPT_DIR}/deploy-agent.sh"
echo ""

echo "Step 3/3: UI Container (ECS)"
echo "============================="
bash "${SCRIPT_DIR}/deploy-ui.sh"
echo ""

echo "=== All deployments complete! ==="
echo ""
echo "Your app is available at the ALB URL:"
aws elbv2 describe-load-balancers \
    --query 'LoadBalancers[?starts_with(LoadBalancerName, `Agent`)].DNSName' \
    --output text 2>/dev/null || echo "(Run this after stacks are fully deployed)"
