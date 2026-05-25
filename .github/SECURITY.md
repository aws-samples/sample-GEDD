# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via [AWS vulnerability reporting](http://aws.amazon.com/security/vulnerability-reporting/).

**Do NOT open a public GitHub issue for security vulnerabilities.**

## Security Best Practices Enforced

- **No secrets in code** — All credentials via environment variables or AWS Secrets Manager
- **Dependency scanning** — Dependabot + Trivy in CI
- **Secret scanning** — TruffleHog in CI pipeline
- **Branch protection** — PRs required for `main`, CI must pass
- **Least-privilege IAM** — Resource-scoped policies, no `*` wildcards
- **Container security** — Non-root user, no hardcoded secrets in Dockerfile
- **Network security** — WAF, restricted security groups, VPC endpoints
- **Encryption** — TLS 1.3 in transit, EFS encryption at rest
