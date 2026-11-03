"""Cognito User Pool for Agent Playground authentication."""

from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class CognitoStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        alb_dns: str = "",
        public_base_url: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self,
            "AgentPlaygroundUserPool",
            user_pool_name="agent-playground-users",
            # Invite-only: an administrator creates users (see SETUP.md). Open self sign-up would let anyone
            # on the internet create an account and spend this account's Bedrock budget.
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(otp=True, sms=False),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Domain for hosted UI (unique per account)
        self.domain = self.user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"agentplayground-{Stack.of(self).account}",
            ),
        )

        # App client: hosted-UI authorization-code flow (SRP only; no plaintext USER_PASSWORD_AUTH)
        self.user_pool_client = self.user_pool.add_client(
            "AppClient",
            user_pool_client_name="app-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_srp=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=[f"{public_base_url}/auth/callback"] if public_base_url else [],
                logout_urls=[public_base_url] if public_base_url else [],
            ),
        )

        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "UserPoolDomain", value=self.domain.domain_name)
