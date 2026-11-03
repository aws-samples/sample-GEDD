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
- **Authentication fails closed** — the app refuses to start unauthenticated on a non-loopback bind; deployed stacks use invite-only Cognito (no self sign-up, optional TOTP MFA)
- **Dependency scanning** — Dependabot (Python, uv, Docker, Actions) + Trivy in CI; Trivy fails the build on fixable HIGH/CRITICAL findings
- **Secret scanning** — TruffleHog in CI pipeline
- **Supply chain** — GitHub Actions pinned to commit SHAs
- **Least-privilege IAM** — resource-scoped policies. The one exception is `ec2:DescribeManagedPrefixLists` (no resource-level support) used to look up CloudFront's prefix list
- **Container security** — non-root user, no compilers or secrets in the runtime image, ECR scan on push
- **Network security** — internal ALB reachable only through a CloudFront VPC origin; CloudFront WAF with per-client rate limiting and AWS managed rules; VPC endpoints for AWS APIs
- **Encryption** — HTTPS for viewers; TLS 1.3 policy on the origin hop when `--cert` is provided (otherwise HTTP inside AWS's private network); EFS encryption at rest
