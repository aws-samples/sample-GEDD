#!/bin/bash
set -euo pipefail

# Deploy GEDD infrastructure (production)
#
# Usage:
#   ./scripts/deploy-infra.sh                          # Dev (no TLS)
#   ./scripts/deploy-infra.sh --cert arn:aws:acm:...   # Production (HTTPS)

CERT_ARN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --cert) CERT_ARN="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$(dirname "$0")/../infra"

pip install -q -r requirements.txt

echo "▸ Synthesizing CDK stacks..."
CDK_CONTEXT=""
if [[ -n "$CERT_ARN" ]]; then
    CDK_CONTEXT="-c certificate_arn=$CERT_ARN"
    echo "  Using TLS certificate: $CERT_ARN"
fi

npx cdk synth $CDK_CONTEXT

echo "▸ Deploying all stacks..."
npx cdk deploy --all --require-approval broadening $CDK_CONTEXT

echo "✓ Infrastructure deployed"
