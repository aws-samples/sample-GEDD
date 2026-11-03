"""CDK App — Agent Playground infrastructure (production)."""

import aws_cdk as cdk

from stacks.agentcore_stack import AgentCoreStack
from stacks.cognito_stack import CognitoStack
from stacks.ecr_stack import EcrStack
from stacks.ecs_stack import EcsStack
from stacks.edge_waf_stack import EdgeWafStack
from stacks.network_stack import NetworkStack

app = cdk.App()

import os

region = app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION") or "us-east-1"
account = os.environ.get("CDK_DEFAULT_ACCOUNT") or None
env = cdk.Environment(account=account, region=region)

certificate_arn = app.node.try_get_context("certificate_arn") or ""
cloudfront_certificate_arn = app.node.try_get_context("cloudfront_certificate_arn") or ""
cloudfront_origin_domain_name = app.node.try_get_context("cloudfront_origin_domain_name") or ""
cloudfront_domain_names_raw = app.node.try_get_context("cloudfront_domain_names") or ""
cloudfront_domain_names = [
    domain.strip()
    for domain in cloudfront_domain_names_raw.split(",")
    if domain.strip()
]
# Auth is always on in deployed stacks: the app refuses to start unauthenticated on a non-loopback bind.
enable_ecs_exec = app.node.try_get_context("enable_ecs_exec") in (True, "true", "1", "yes")

# ── Stacks ────────────────────────────────────────────────────────────────────

# CloudFront-scope WAF must be created in us-east-1; it is referenced cross-region by the distribution.
edge_waf = EdgeWafStack(
    app, "AgentPlayground-EdgeWaf",
    env=cdk.Environment(account=account, region="us-east-1"),
    cross_region_references=True,
)

network = NetworkStack(
    app, "AgentPlayground-Network",
    web_acl_arn=edge_waf.web_acl.attr_arn,
    cross_region_references=True,
    certificate_arn=certificate_arn,
    cloudfront_domain_names=cloudfront_domain_names,
    cloudfront_certificate_arn=cloudfront_certificate_arn,
    cloudfront_origin_domain_name=cloudfront_origin_domain_name,
    env=env,
)

ecr = EcrStack(app, "AgentPlayground-Ecr", env=env)
agentcore = AgentCoreStack(app, "AgentPlayground-AgentCore", env=env)

cognito_stack = CognitoStack(
    app, "AgentPlayground-Cognito",
    alb_dns=network.alb.load_balancer_dns_name,
    public_base_url=f"https://{network.distribution.distribution_domain_name}",
    env=env,
)

ecs = EcsStack(
    app, "AgentPlayground-Ecs",
    vpc=network.vpc,
    alb=network.alb,
    ecs_sg=network.ecs_sg,
    ecr_repo=ecr.repo,
    user_pool_id=cognito_stack.user_pool.user_pool_id,
    user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
    user_pool_domain=cognito_stack.domain.domain_name,
    public_base_url=f"https://{network.distribution.distribution_domain_name}",
    agentcore_agent_id_param=agentcore.agent_id_param,
    certificate_arn=certificate_arn,
    enable_app_auth=True,
    enable_ecs_exec=enable_ecs_exec,
    env=env,
)

app.synth()
