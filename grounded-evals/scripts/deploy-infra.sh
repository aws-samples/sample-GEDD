#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground Infrastructure ==="

cd "$(dirname "$0")/../infra"

pip install -r requirements.txt -q

echo "Synthesizing CloudFormation templates..."
cdk synth

echo "Deploying all stacks..."
cdk deploy --all --require-approval broadening

echo "=== Infrastructure deployment complete ==="
echo ""
echo "Next steps:"
echo "  1. Run scripts/deploy-agent.sh to deploy the AgentCore agent"
echo "  2. Run scripts/deploy-ui.sh to build and push the UI container"
