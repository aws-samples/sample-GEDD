#!/bin/bash
set -euo pipefail

# Deploy GEDD infrastructure (production)
#
# Usage:
#   ./scripts/deploy-infra.sh                                      # CloudFront + HTTP ALB origin
#   ./scripts/deploy-infra.sh --cert arn:aws:acm:...               # Direct ALB HTTPS listener
#   ./scripts/deploy-infra.sh --cloudfront-domain app.example.com \
#     --cloudfront-cert arn:aws:acm:us-east-1:...:certificate/...  # CloudFront alias

CERT_ARN=""
CLOUDFRONT_CERT_ARN=""
CLOUDFRONT_DOMAIN_NAMES=""
CLOUDFRONT_ORIGIN_DOMAIN_NAME=""
REGION="${AWS_REGION:-us-east-1}"
while [[ $# -gt 0 ]]; do
    case $1 in
        --cert) CERT_ARN="$2"; shift 2 ;;
        --cloudfront-cert) CLOUDFRONT_CERT_ARN="$2"; shift 2 ;;
        --cloudfront-domain) CLOUDFRONT_DOMAIN_NAMES="$2"; shift 2 ;;
        --cloudfront-origin-domain) CLOUDFRONT_ORIGIN_DOMAIN_NAME="$2"; shift 2 ;;
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
if [[ -n "$CLOUDFRONT_CERT_ARN" ]]; then
    CDK_CONTEXT="$CDK_CONTEXT -c cloudfront_certificate_arn=$CLOUDFRONT_CERT_ARN"
    echo "  Using CloudFront certificate: $CLOUDFRONT_CERT_ARN"
fi
if [[ -n "$CLOUDFRONT_DOMAIN_NAMES" ]]; then
    CDK_CONTEXT="$CDK_CONTEXT -c cloudfront_domain_names=$CLOUDFRONT_DOMAIN_NAMES"
    echo "  Using CloudFront aliases: $CLOUDFRONT_DOMAIN_NAMES"
fi
if [[ -n "$CLOUDFRONT_ORIGIN_DOMAIN_NAME" ]]; then
    CDK_CONTEXT="$CDK_CONTEXT -c cloudfront_origin_domain_name=$CLOUDFRONT_ORIGIN_DOMAIN_NAME"
    echo "  Using CloudFront HTTPS origin domain: $CLOUDFRONT_ORIGIN_DOMAIN_NAME"
fi

npx cdk synth $CDK_CONTEXT

echo "▸ Deploying all stacks..."
npx cdk deploy --all --require-approval broadening $CDK_CONTEXT

echo "✓ Infrastructure deployed"
echo "CloudFront URL:"
aws cloudformation describe-stacks \
    --stack-name AgentPlayground-Network \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' \
    --output text 2>/dev/null || echo "(CloudFront output will be available after stack completion)"
