#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground to AgentCore ==="

REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(dirname "$0")"
AGENT_DIR="${SCRIPT_DIR}/../agentcore"

cd "$AGENT_DIR"

# Install AgentCore CLI if not present
if ! command -v agentcore &> /dev/null; then
    echo "Installing AgentCore CLI..."
    npm install -g @aws/agentcore
fi

# Install agent dependencies
echo "Installing agent dependencies..."
pip install -e . -q

# Deploy to AgentCore
echo "Deploying agent to AgentCore Runtime..."
agentcore deploy

# Capture the agent ID from deployment output and store in SSM
AGENT_ID=$(agentcore list --json | python3 -c "import sys, json; agents=json.load(sys.stdin); print(agents[0]['id'] if agents else '')")

if [ -n "$AGENT_ID" ]; then
    echo "Agent deployed with ID: $AGENT_ID"
    aws ssm put-parameter \
        --name "/agent-playground/agentcore-agent-id" \
        --value "$AGENT_ID" \
        --type String \
        --overwrite \
        --region "$REGION"
    echo "Agent ID stored in SSM parameter: /agent-playground/agentcore-agent-id"
else
    echo "WARNING: Could not determine agent ID from deployment output"
    echo "Manually set the SSM parameter /agent-playground/agentcore-agent-id"
fi

echo ""
echo "=== AgentCore deployment complete ==="
echo "Next: Run scripts/deploy-ui.sh to deploy the UI"
