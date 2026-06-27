---
inclusion: fileMatch
fileMatchPattern: "**/infra/**"
---

# GEDD Infrastructure Guide

## Overview
AWS CDK (Python) infrastructure in `grounded-evals/infra/`.

## Stack Composition
Defined in `infra/app.py`, deployed in order:

1. **NetworkStack** — VPC, ALB, CloudFront distribution
2. **EcrStack** — ECR container registry
3. **CognitoStack** — User pool, app client, hosted UI domain
4. **EcsStack** — ECS Fargate task definition and service
5. **AgentCoreStack** — Optional AWS AgentCore runtime integration

## CDK Conventions
- Each stack is a self-contained construct in `infra/stacks/<name>_stack.py`
- Configuration via `infra/cdk.json` context values
- Cross-stack references via constructor parameters (not Fn::Import)

```python
# infra/app.py pattern
network = NetworkStack(app, "Network", env=env)
ecr = EcrStack(app, "ECR", env=env)
ecs = EcsStack(app, "ECS", vpc=network.vpc, repository=ecr.repository, env=env)
```

## Deployment
```bash
cd grounded-evals/infra
pip install -r requirements.txt
cdk bootstrap    # one-time
cdk deploy --all
```

## Key Outputs
- `CloudFrontUrl` — Public HTTPS endpoint
- Custom domain: `--cloudfront-domain` + ACM cert from us-east-1

## Docker Image
From `grounded-evals/Dockerfile`:
- Base: `python:3.11-slim`
- Runs as non-root `appuser`
- Healthcheck on `/health`
- Exposes port 8080
- Entry: `python -m grounded_evals.app`

## Environment Variables at Runtime
| Variable | Purpose |
|----------|---------|
| `AWS_REGION` | Bedrock region |
| `COGNITO_USER_POOL_ID` | Auth user pool |
| `COGNITO_CLIENT_ID` | Auth app client |
| `STORAGE_SECRET` | Session encryption (auto-gen if unset) |
| `ADMIN_PASSWORD` | Simple auth for workshops |

## CI Integration
GitHub Actions `cdk-synth` job validates infrastructure:
```bash
cdk synth --no-lookups
```
This runs on every push/PR to catch CDK errors before deploy.

## Security
- IAM role-based Bedrock access (no API keys in containers)
- Fargate task isolation within VPC
- CloudFront terminates public HTTPS
- Cognito for user authentication
- ECR image scanning enabled
