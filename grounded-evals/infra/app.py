"""CDK App — Agent Playground infrastructure."""

import aws_cdk as cdk

from stacks.agentcore_stack import AgentCoreStack
from stacks.cognito_stack import CognitoStack
from stacks.ecr_stack import EcrStack
from stacks.ecs_stack import EcsStack
from stacks.network_stack import NetworkStack

app = cdk.App()

env = cdk.Environment(
    region=app.node.try_get_context("region") or "us-east-1",
)

network = NetworkStack(app, "AgentPlayground-Network", env=env)
ecr = EcrStack(app, "AgentPlayground-Ecr", env=env)
agentcore = AgentCoreStack(app, "AgentPlayground-AgentCore", env=env)

cognito_stack = CognitoStack(
    app,
    "AgentPlayground-Cognito",
    alb_dns=network.alb.load_balancer_dns_name,
    env=env,
)

ecs = EcsStack(
    app,
    "AgentPlayground-Ecs",
    vpc=network.vpc,
    alb=network.alb,
    ecs_sg=network.ecs_sg,
    ecr_repo=ecr.repo,
    user_pool_id=cognito_stack.user_pool.user_pool_id,
    user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
    user_pool_domain=cognito_stack.domain.domain_name,
    agentcore_agent_id="",
    env=env,
)

app.synth()
