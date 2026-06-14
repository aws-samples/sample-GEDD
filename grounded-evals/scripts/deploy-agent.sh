#!/bin/bash
set -euo pipefail

echo "=== Deploying Agent Playground to AgentCore ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_AGENTCORE_CLI="/private/tmp/agentcore-cli-runner/node_modules/.bin/agentcore"
AGENTCORE_CLI="${AGENTCORE_CLI:-}"
AGENTCORE_TARGET="${AGENTCORE_TARGET:-default}"
AGENTCORE_PROJECT_DIR="${AGENTCORE_PROJECT_DIR:-${SCRIPT_DIR}/../agentcore}"

if [[ -z "$AGENTCORE_CLI" ]]; then
    if [[ -x "$DEFAULT_AGENTCORE_CLI" ]]; then
        AGENTCORE_CLI="$DEFAULT_AGENTCORE_CLI"
    elif command -v agentcore &> /dev/null; then
        AGENTCORE_CLI="$(command -v agentcore)"
    else
        echo "ERROR: Could not find an AgentCore CLI."
        echo "Set AGENTCORE_CLI to a working binary."
        echo "Known-good local path on this machine:"
        echo "  $DEFAULT_AGENTCORE_CLI"
        exit 1
    fi
fi

if [[ ! -x "$AGENTCORE_CLI" ]]; then
    echo "ERROR: AGENTCORE_CLI is not executable: $AGENTCORE_CLI"
    exit 1
fi

if [[ ! -d "$AGENTCORE_PROJECT_DIR" ]]; then
    echo "ERROR: AgentCore project directory not found: $AGENTCORE_PROJECT_DIR"
    exit 1
fi

if [[ ! -f "$AGENTCORE_PROJECT_DIR/agentcore.json" ]]; then
    echo "ERROR: No AgentCore project config found in $AGENTCORE_PROJECT_DIR"
    echo "Expected: $AGENTCORE_PROJECT_DIR/agentcore.json"
    echo "If your project lives elsewhere, set AGENTCORE_PROJECT_DIR=/path/to/project"
    exit 1
fi

cd "$AGENTCORE_PROJECT_DIR"

if [[ -f "pyproject.toml" ]]; then
    echo "Installing agent dependencies..."
    pip install -e . -q
fi

echo "Using AgentCore CLI: $AGENTCORE_CLI"
"$AGENTCORE_CLI" --version

# Deploy to AgentCore
echo "Deploying agent to AgentCore Runtime..."
"$AGENTCORE_CLI" deploy --target "$AGENTCORE_TARGET" -y

echo ""
echo "=== AgentCore deployment complete ==="
echo "Check deployed resources:"
echo "\"$AGENTCORE_CLI\" status --target \"$AGENTCORE_TARGET\" --json"
echo "Invoke the deployed runtime:"
echo "\"$AGENTCORE_CLI\" invoke --target \"$AGENTCORE_TARGET\" --json --prompt 'status'"
echo "Next: Run scripts/deploy-ui.sh to deploy the UI"
