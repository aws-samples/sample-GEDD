"""Amazon Bedrock AgentCore Harness client.

Two separate boto3 service clients:
  bedrock-agentcore-control  — create / get Harnesses  (control plane)
  bedrock-agentcore          — invoke Harnesses         (data plane)

Harness is currently in preview in four regions only:
  us-east-1 · us-west-2 · eu-central-1 · ap-southeast-2

Requirements: boto3 >= 1.42.94
"""

from __future__ import annotations

import os
import re
import time
import uuid

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

HARNESS_REGIONS: frozenset[str] = frozenset(
    {"us-east-1", "us-west-2", "eu-central-1", "ap-southeast-2"}
)

_HARNESS_CLIENT_AVAILABLE: bool | None = None  # lazy check


def _check_harness_available(region: str) -> bool:
    """Return True if the Harness data-plane client can be created (boto3 version guard)."""
    global _HARNESS_CLIENT_AVAILABLE
    if _HARNESS_CLIENT_AVAILABLE is not None:
        return _HARNESS_CLIENT_AVAILABLE
    try:
        boto3.client("bedrock-agentcore", region_name=region)
        _HARNESS_CLIENT_AVAILABLE = True
    except Exception:
        _HARNESS_CLIENT_AVAILABLE = False
    return _HARNESS_CLIENT_AVAILABLE


def slugify(name: str) -> str:
    """Convert an agent name to a valid Harness name (max 63 chars)."""
    slug = re.sub(r"[^a-zA-Z0-9\-]", "-", name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return f"gedd-{slug}"[:63] or "gedd-agent"


class HarnessClient:
    """Thin wrapper over the AgentCore Harness control + data plane APIs."""

    def __init__(self, region: str | None = None) -> None:
        self.region: str = (
            region
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-1"
        )
        self._control: boto3.client | None = None  # type: ignore[type-arg]
        self._data: boto3.client | None = None  # type: ignore[type-arg]

    # ── Lazy boto3 clients ────────────────────────────────────────────────────

    @property
    def control(self):  # noqa: ANN201
        if self._control is None:
            self._control = boto3.client(
                "bedrock-agentcore-control", region_name=self.region
            )
        return self._control

    @property
    def data(self):  # noqa: ANN201
        if self._data is None:
            self._data = boto3.client("bedrock-agentcore", region_name=self.region)
        return self._data

    # ── Guard helpers ─────────────────────────────────────────────────────────

    def is_region_supported(self) -> bool:
        return self.region in HARNESS_REGIONS

    def is_boto3_compatible(self) -> bool:
        return _check_harness_available(self.region)

    # ── IAM role discovery ────────────────────────────────────────────────────

    def discover_execution_role_arn(self) -> str:
        """
        Return an execution role ARN from (in order):
          1. HARNESS_EXECUTION_ROLE_ARN env var
          2. Derived from STS caller identity (assumes role name GEDDHarnessExecutionRole)
          3. Empty string — caller must prompt the user
        """
        env_arn = os.environ.get("HARNESS_EXECUTION_ROLE_ARN", "").strip()
        if env_arn:
            return env_arn
        try:
            sts = boto3.client("sts", region_name=self.region)
            account = sts.get_caller_identity()["Account"]
            return f"arn:aws:iam::{account}:role/GEDDHarnessExecutionRole"
        except Exception:
            return ""

    # ── Control plane ─────────────────────────────────────────────────────────

    def create_harness(
        self,
        agent_name: str,
        system_prompt: str,
        execution_role_arn: str,
    ) -> dict[str, str]:
        """
        Create a new Harness and return {'arn', 'status', 'name'}.
        Raises RuntimeError with a PM-friendly message on failure.
        """
        name = slugify(agent_name)
        try:
            resp = self.control.create_harness(
                harnessName=name,
                executionRoleArn=execution_role_arn,
                systemPrompt=[{"text": system_prompt}],
            )
            return {
                "arn": resp["arn"],
                "status": resp.get("status", "CREATING"),
                "name": name,
            }
        except NoCredentialsError:
            raise RuntimeError(
                "AWS credentials not found. Configure your AWS CLI or IAM role."
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            if code in ("AccessDeniedException", "UnauthorizedException"):
                raise RuntimeError(
                    "IAM permission denied. Your role needs "
                    "bedrock-agentcore:CreateHarness and iam:PassRole."
                )
            if code == "ValidationException":
                raise RuntimeError(f"Invalid parameters: {msg}")
            if code == "ResourceLimitExceededException":
                raise RuntimeError("Harness quota reached. Delete an existing harness first.")
            raise RuntimeError(f"AWS error ({code}): {msg}")

    def get_harness_status(self, harness_arn: str) -> str:
        """
        Return the current harness status string:
        CREATING | READY | FAILED | DELETING | NOT_FOUND | UNKNOWN
        """
        try:
            resp = self.control.get_harness(harnessArn=harness_arn)
            return resp.get("status", "UNKNOWN")
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                return "NOT_FOUND"
            return "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def wait_for_ready(self, harness_arn: str, timeout_sec: int = 90) -> str:
        """
        Poll every 3 s until status is terminal (READY/FAILED/NOT_FOUND) or timeout.
        Returns the final status string.
        """
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            status = self.get_harness_status(harness_arn)
            if status in ("READY", "FAILED", "NOT_FOUND"):
                return status
            time.sleep(3)
        return "TIMEOUT"

    # ── Data plane ────────────────────────────────────────────────────────────

    def invoke_query(
        self,
        harness_arn: str,
        model_id: str,
        system_prompt: str,
        query: str,
    ) -> str:
        """
        Invoke one query against the Harness with a fresh isolated session.
        Returns the agent's full text response.
        Raises RuntimeError on hard failures.
        """
        try:
            response = self.data.invoke_harness(
                harnessArn=harness_arn,
                runtimeSessionId=str(uuid.uuid4()),   # fresh session = no cross-query state
                model={"bedrockModelConfig": {"modelId": model_id}},
                systemPrompt=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": query}]}],
            )
            parts: list[str] = []
            for event in response["stream"]:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        parts.append(delta["text"])
                elif "runtimeClientError" in event:
                    err = event["runtimeClientError"]
                    raise RuntimeError(f"Harness stream error: {err.get('message', 'unknown')}")
            return "".join(parts)

        except NoCredentialsError:
            raise RuntimeError("AWS credentials not found.")
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            if code == "ResourceNotFoundException":
                raise RuntimeError(
                    "Harness not found — verify the ARN and region match."
                )
            if code == "ThrottlingException":
                raise RuntimeError("Rate limit hit. Slow down requests or increase quota.")
            if code in ("AccessDeniedException", "UnauthorizedException"):
                raise RuntimeError(f"IAM permission denied: bedrock-agentcore:InvokeHarness")
            raise RuntimeError(f"AWS error ({code}): {msg}")


# ── Convenience factory ───────────────────────────────────────────────────────

def get_harness_client(region: str | None = None) -> HarnessClient:
    return HarnessClient(region)
