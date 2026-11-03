"""CloudFront-scope WAF (must live in us-east-1): per-client rate limiting plus AWS managed rules."""

from aws_cdk import Stack
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct


def _visibility(name: str) -> wafv2.CfnWebACL.VisibilityConfigProperty:
    return wafv2.CfnWebACL.VisibilityConfigProperty(
        cloud_watch_metrics_enabled=True, metric_name=name, sampled_requests_enabled=True,
    )


def _managed(name: str, priority: int, metric: str) -> wafv2.CfnWebACL.RuleProperty:
    return wafv2.CfnWebACL.RuleProperty(
        name=name,
        priority=priority,
        override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
        statement=wafv2.CfnWebACL.StatementProperty(
            managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(vendor_name="AWS", name=name),
        ),
        visibility_config=_visibility(metric),
    )


class EdgeWafStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, rate_limit_per_5min: int = 1000, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.web_acl = wafv2.CfnWebACL(
            self, "EdgeWebAcl",
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=_visibility("GeddEdgeWaf"),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitPerClientIp",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=rate_limit_per_5min, aggregate_key_type="IP",
                        ),
                    ),
                    visibility_config=_visibility("EdgeRateLimit"),
                ),
                _managed("AWSManagedRulesCommonRuleSet", 2, "EdgeCommonRules"),
                _managed("AWSManagedRulesKnownBadInputsRuleSet", 3, "EdgeKnownBadInputs"),
                _managed("AWSManagedRulesAmazonIpReputationList", 4, "EdgeIpReputation"),
            ],
        )
