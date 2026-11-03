"""IAM role and configuration for the AgentCore runtime agent."""

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class AgentCoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM role that the AgentCore runtime assumes
        region = Stack.of(self).region
        account = Stack.of(self).account
        self.runtime_role = iam.Role(
            self,
            "AgentCoreRuntimeRole",
            # AgentCore Runtime assumes roles via its own service principal; confused-deputy conditions pin it
            # to this account and its runtimes.
            assumed_by=iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account}:*"},
                },
            ),
            description="Role for the GEDD AgentCore runtime",
        )

        # Bedrock model invocation (coach LLM calls and eval multi-model calls), scoped to foundation models
        # and this account's inference profiles; cross-region inference profiles route to any region's models.
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account}:inference-profile/*",
                ],
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
