"""ECS Fargate service — production hardened.

Changes from dev:
- Secrets from Secrets Manager (STORAGE_SECRET, ADMIN_PASSWORD)
- EFS for persistent session storage
- ALB Cognito authentication action
- Restricted IAM policies with resource scoping
- Auto-scaling with request-count metric
"""

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_elasticloadbalancingv2_actions as elbv2_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class EcsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        alb: elbv2.IApplicationLoadBalancer,
        listener: elbv2.IApplicationListener,
        ecs_sg: ec2.ISecurityGroup,
        ecr_repo: ecr.IRepository,
        user_pool_id: str = "",
        user_pool_client_id: str = "",
        user_pool_domain: str = "",
        agentcore_agent_id: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region
        account = Stack.of(self).account

        # ── Secrets Manager ───────────────────────────────────────────────────
        self.storage_secret = secretsmanager.Secret(
            self, "StorageSecret",
            secret_name="agent-playground/storage-secret",
            description="NiceGUI session cookie signing secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64, exclude_punctuation=True,
            ),
        )

        self.admin_secret = secretsmanager.Secret(
            self, "AdminSecret",
            secret_name="agent-playground/admin-password",
            description="Fallback admin password (used when Cognito is unavailable)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=32, exclude_punctuation=False,
            ),
        )

        # ── EFS for persistent session storage ────────────────────────────────
        efs_sg = ec2.SecurityGroup(
            self, "EfsSg", vpc=vpc,
            description="EFS — NFS from ECS tasks",
            allow_all_outbound=False,
        )
        efs_sg.add_ingress_rule(ecs_sg, ec2.Port.tcp(2049), "NFS from ECS")

        file_system = efs.FileSystem(
            self, "SessionStorage",
            vpc=vpc,
            security_group=efs_sg,
            encrypted=True,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            removal_policy=RemovalPolicy.RETAIN,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        access_point = file_system.add_access_point(
            "AppAccessPoint",
            path="/nicegui-storage",
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
            posix_user=efs.PosixUser(uid="1000", gid="1000"),
        )

        # ── ECS Cluster ───────────────────────────────────────────────────────
        cluster = ecs.Cluster(
            self, "Cluster", vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.ENABLED,
        )

        # ── IAM Roles ─────────────────────────────────────────────────────────
        execution_role = iam.Role(
            self, "ExecRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
            ],
        )
        # Allow pulling secrets into env vars
        self.storage_secret.grant_read(execution_role)
        self.admin_secret.grant_read(execution_role)

        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=[f"arn:aws:bedrock:{region}::foundation-model/*"],
        ))
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeAgent"],
            resources=[f"arn:aws:bedrock:{region}:{account}:agent/*"],
        ))
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{region}:{account}:parameter/agent-playground/*"],
        ))
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["cognito-idp:InitiateAuth", "cognito-idp:RespondToAuthChallenge"],
            resources=[f"arn:aws:cognito-idp:{region}:{account}:userpool/*"],
        ))

        # ── Task Definition ───────────────────────────────────────────────────
        task_def = ecs.FargateTaskDefinition(
            self, "TaskDef",
            cpu=512, memory_limit_mib=1024,
            execution_role=execution_role,
            task_role=task_role,
        )

        # EFS volume
        task_def.add_volume(
            name="session-storage",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point.access_point_id, iam="ENABLED",
                ),
            ),
        )
        file_system.grant_read_write(task_role)

        container = task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_ecr_repository(ecr_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="gedd", log_retention=logs.RetentionDays.ONE_MONTH,
            ),
            environment={
                "HOST": "0.0.0.0",
                "PORT": "8080",
                "NICEGUI_RELOAD": "false",
                "AWS_REGION": region,
                "AGENTCORE_AGENT_ID": agentcore_agent_id,
                "COGNITO_USER_POOL_ID": user_pool_id,
                "COGNITO_CLIENT_ID": user_pool_client_id,
                "COGNITO_DOMAIN": user_pool_domain,
                "NICEGUI_STORAGE_PATH": "/mnt/storage",
            },
            secrets={
                "STORAGE_SECRET": ecs.Secret.from_secrets_manager(self.storage_secret),
                "ADMIN_PASSWORD": ecs.Secret.from_secrets_manager(self.admin_secret),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8080))
        container.add_mount_points(ecs.MountPoint(
            container_path="/mnt/storage",
            source_volume="session-storage",
            read_only=False,
        ))

        # ── Target Group ──────────────────────────────────────────────────────
        target_group = elbv2.ApplicationTargetGroup(
            self, "Tg", vpc=vpc,
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            stickiness_cookie_duration=Duration.hours(1),
        )

        # ── Fargate Service ───────────────────────────────────────────────────
        service = ecs.FargateService(
            self, "Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            security_groups=[ecs_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            enable_execute_command=True,
        )
        target_group.add_target(service)

        # ── ALB Listener Rule (Cognito auth if configured) ────────────────────
        if user_pool_id and user_pool_client_id and user_pool_domain:
            from aws_cdk import aws_cognito as cognito

            imported_pool = cognito.UserPool.from_user_pool_id(self, "ImportedPool", user_pool_id)
            imported_client = cognito.UserPoolClient.from_user_pool_client_id(self, "ImportedClient", user_pool_client_id)
            imported_domain = cognito.UserPoolDomain.from_domain_name(self, "ImportedDomain", user_pool_domain)

            elbv2.ApplicationListenerRule(
                self, "CognitoAuthRule",
                listener=listener,
                priority=10,
                conditions=[elbv2.ListenerCondition.path_patterns(["/*"])],
                action=elbv2_actions.AuthenticateCognitoAction(
                    user_pool=imported_pool,
                    user_pool_client=imported_client,
                    user_pool_domain=imported_domain,
                    next=elbv2.ListenerAction.forward([target_group]),
                ),
            )
        else:
            elbv2.ApplicationListenerRule(
                self, "ForwardRule",
                listener=listener,
                priority=50,
                conditions=[elbv2.ListenerCondition.path_patterns(["/*"])],
                action=elbv2.ListenerAction.forward([target_group]),
            )

        # ── Auto-scaling ──────────────────────────────────────────────────────
        scaling = service.auto_scale_task_count(min_capacity=1, max_capacity=4)
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

