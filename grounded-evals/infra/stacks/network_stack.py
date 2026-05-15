"""VPC, ALB, and Security Groups for Agent Playground."""

from aws_cdk import Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from constructs import Construct


class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "AgentPlaygroundVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            description="ALB security group - allows HTTPS inbound",
            allow_all_outbound=True,
        )
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS",
        )
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP (redirect to HTTPS)",
        )

        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "AgentPlaygroundAlb",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_sg,
        )
        # WebSocket connections need long idle timeout
        self.alb.set_attribute("idle_timeout.timeout_seconds", "3600")

        self.ecs_sg = ec2.SecurityGroup(
            self,
            "EcsSecurityGroup",
            vpc=self.vpc,
            description="ECS tasks - allows traffic from ALB only",
            allow_all_outbound=True,
        )
        self.ecs_sg.add_ingress_rule(
            self.alb_sg,
            ec2.Port.tcp(8080),
            "Allow traffic from ALB",
        )
