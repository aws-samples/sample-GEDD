"""IAM role and configuration for the AgentCore runtime agent."""

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class AgentCoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM role that the AgentCore runtime assumes
        self.runtime_role = iam.Role(
            self,
            "AgentCoreRuntimeRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Agent Playground AgentCore runtime",
        )

        # Bedrock model invocation (for coach LLM calls and eval multi-model calls)
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        # SSM parameter to store the deployed agent ID
        # Populated after `agentcore deploy` via scripts/deploy-agent.sh
        self.agent_id_param = ssm.StringParameter(
            self,
            "AgentIdParam",
            parameter_name="/agent-playground/agentcore-agent-id",
            string_value="PLACEHOLDER",
            description="AgentCore agent ID — updated by deploy-agent.sh after deployment",
        )

        CfnOutput(
            self,
            "RuntimeRoleArn",
            value=self.runtime_role.role_arn,
            description="ARN of the IAM role for AgentCore runtime",
        )

        CfnOutput(
            self,
            "AgentIdParamName",
            value=self.agent_id_param.parameter_name,
            description="SSM parameter storing the AgentCore agent ID",
        )
