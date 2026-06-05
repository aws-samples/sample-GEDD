"""VPC, ALB, CloudFront, WAF, and Security Groups for Agent Playground."""

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct


class NetworkStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str = "",
        certificate_arn: str = "",
        cloudfront_domain_names: list[str] | None = None,
        cloudfront_certificate_arn: str = "",
        cloudfront_origin_domain_name: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cloudfront_domain_names = cloudfront_domain_names or []

        # ── VPC: 2 AZs, public + private subnets ─────────────────────────────
        self.vpc = ec2.Vpc(
            self, "Vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24),
            ],
        )

        # ── Security Groups ───────────────────────────────────────────────────
        self.alb_sg = ec2.SecurityGroup(
            self, "AlbSg", vpc=self.vpc,
            description="ALB - HTTPS inbound only",
            allow_all_outbound=False,
        )
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP (redirect)")

        self.ecs_sg = ec2.SecurityGroup(
            self, "EcsSg", vpc=self.vpc,
            description="ECS tasks - ALB ingress only",
            allow_all_outbound=False,
        )
        self.ecs_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(8080), "From ALB")
        # Egress: HTTPS to AWS services + NAT
        self.ecs_sg.add_egress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS to AWS APIs")

        # ALB → ECS egress
        self.alb_sg.add_egress_rule(self.ecs_sg, ec2.Port.tcp(8080), "To ECS targets")

        # ── Application Load Balancer ─────────────────────────────────────────
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "Alb", vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_sg,
        )
        self.alb.set_attribute("idle_timeout.timeout_seconds", "3600")
        self.alb.set_attribute("routing.http.drop_invalid_header_fields.enabled", "true")

        # ── TLS Certificate ───────────────────────────────────────────────────
        if certificate_arn:
            certificate = acm.Certificate.from_certificate_arn(self, "Cert", certificate_arn)
        else:
            # Create a DNS-validated cert (requires domain_name and Route53 hosted zone)
            certificate = None

        # ── HTTPS Listener ────────────────────────────────────────────────────
        if certificate:
            self.https_listener = self.alb.add_listener(
                "HttpsListener", port=443,
                certificates=[certificate],
                ssl_policy=elbv2.SslPolicy.TLS13_RES,
                open=False,
                default_action=elbv2.ListenerAction.fixed_response(
                    status_code=503, content_type="text/plain", message_body="Service starting",
                ),
            )
            # HTTP → HTTPS redirect
            self.alb.add_listener(
                "HttpRedirect", port=80, open=False,
                default_action=elbv2.ListenerAction.redirect(
                    protocol="HTTPS", port="443", permanent=True,
                ),
            )
            self.listener = self.https_listener
        else:
            # Fallback: HTTP-only (for dev/testing without a domain)
            self.listener = self.alb.add_listener(
                "HttpListener", port=80, open=False,
                default_action=elbv2.ListenerAction.fixed_response(
                    status_code=503, content_type="text/plain", message_body="Service starting",
                ),
            )

        # ── WAF WebACL ────────────────────────────────────────────────────────
        waf_acl = wafv2.CfnWebACL(
            self, "WafAcl",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="AgentPlaygroundWaf",
                sampled_requests_enabled=True,
            ),
            rules=[
                # Rate limiting: 1000 requests per 5 min per IP
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimit",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=1000,
                            aggregate_key_type="IP",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimit",
                        sampled_requests_enabled=True,
                    ),
                ),
                # AWS Managed Rules: Common Rule Set
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedCommonRules",
                    priority=2,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRules",
                        sampled_requests_enabled=True,
                    ),
                ),
                # AWS Managed Rules: Known Bad Inputs
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedKnownBadInputs",
                    priority=3,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesKnownBadInputsRuleSet",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="KnownBadInputs",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # Associate WAF with ALB
        wafv2.CfnWebACLAssociation(
            self, "WafAlbAssociation",
            resource_arn=self.alb.load_balancer_arn,
            web_acl_arn=waf_acl.attr_arn,
        )

        # ── VPC Endpoints (keep AWS API traffic private) ────────────────────────
        endpoint_sg = ec2.SecurityGroup(
            self, "EndpointSg", vpc=self.vpc,
            description="VPC endpoints - HTTPS from ECS",
            allow_all_outbound=False,
        )
        endpoint_sg.add_ingress_rule(self.ecs_sg, ec2.Port.tcp(443), "HTTPS from ECS")

        private_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)

        for svc_name in ["bedrock-runtime", "bedrock-agent-runtime", "ssm", "secretsmanager", "logs", "sts"]:
            self.vpc.add_interface_endpoint(
                f"Ep-{svc_name}",
                service=ec2.InterfaceVpcEndpointAwsService(svc_name),
                subnets=private_subnets,
                security_groups=[endpoint_sg],
            )

        self.vpc.add_interface_endpoint("Ep-ecr-api", service=ec2.InterfaceVpcEndpointAwsService.ECR, subnets=private_subnets, security_groups=[endpoint_sg])
        self.vpc.add_interface_endpoint("Ep-ecr-dkr", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER, subnets=private_subnets, security_groups=[endpoint_sg])
        self.vpc.add_gateway_endpoint("Ep-s3", service=ec2.GatewayVpcEndpointAwsService.S3, subnets=[private_subnets])

        # ── CloudFront public domain ─────────────────────────────────────────
        # NiceGUI uses cookies, dynamic pages, and websockets, so this behaves
        # like a secure public edge endpoint rather than a static-cache layer.
        # The managed policy forwards viewer headers/cookies/query strings but
        # strips Host so the ALB receives its own origin host.
        all_viewer_except_host = cloudfront.OriginRequestPolicy.from_origin_request_policy_id(
            self,
            "AllViewerExceptHostHeaderPolicy",
            "b689b0a8-53d0-40ab-baf2-68738e2966ac",
        )

        if cloudfront_origin_domain_name:
            cloudfront_origin = origins.HttpOrigin(
                cloudfront_origin_domain_name,
                protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                read_timeout=Duration.seconds(60),
                keepalive_timeout=Duration.seconds(60),
            )
        else:
            cloudfront_origin = origins.LoadBalancerV2Origin(
                self.alb,
                protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                read_timeout=Duration.seconds(60),
                keepalive_timeout=Duration.seconds(60),
            )

        distribution_props = {
            "comment": "GEDD web app public edge distribution",
            "default_behavior": cloudfront.BehaviorOptions(
                origin=cloudfront_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=all_viewer_except_host,
                compress=True,
            ),
            "http_version": cloudfront.HttpVersion.HTTP2_AND_3,
            "price_class": cloudfront.PriceClass.PRICE_CLASS_100,
            "enable_ipv6": True,
        }

        if cloudfront_certificate_arn and cloudfront_domain_names:
            distribution_props["certificate"] = acm.Certificate.from_certificate_arn(
                self,
                "CloudFrontCert",
                cloudfront_certificate_arn,
            )
            distribution_props["domain_names"] = cloudfront_domain_names

        self.distribution = cloudfront.Distribution(
            self,
            "WebDistribution",
            **distribution_props,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "AlbDns", value=self.alb.load_balancer_dns_name)
        CfnOutput(self, "CloudFrontDomainName", value=self.distribution.distribution_domain_name)
        CfnOutput(self, "CloudFrontUrl", value=f"https://{self.distribution.distribution_domain_name}")
        if cloudfront_domain_names:
            CfnOutput(self, "CloudFrontAliases", value=",".join(cloudfront_domain_names))
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
