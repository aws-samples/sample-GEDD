#!/usr/bin/env python3
"""Export live AwsGdprAuditor responses for the 50 AWS GDPR golden queries."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:384790854332:runtime/"
    "awsgdprauditor_AwsGdprAuditor-J0qdk36nwG"
)
DEFAULT_OUTPUT = SRC_ROOT / "grounded_evals" / "ui" / "gdpr_auditor_runtime_snapshot.py"

sys.path.insert(0, str(SRC_ROOT))

from grounded_evals.ui.gdpr_auditor_demo import GDPR_AUDITOR_TRACES  # noqa: E402


_UNICODE_REPLACEMENTS = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u00a0": " ",
})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export live AwsGdprAuditor responses for the AWS GDPR golden queries.",
    )
    parser.add_argument(
        "--runtime-arn",
        default=os.environ.get("AWS_GDPR_AUDITOR_RUNTIME_ARN", DEFAULT_RUNTIME_ARN),
        help="Bedrock AgentCore runtime ARN to invoke.",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region for the AgentCore runtime client.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated Python snapshot module.",
    )
    parser.add_argument(
        "--runtime-name",
        default=os.environ.get("AWS_GDPR_AUDITOR_RUNTIME_NAME", "AwsGdprAuditor"),
        help="Human-readable runtime name recorded in the snapshot metadata.",
    )
    return parser.parse_args()


def _parse_sse_text(raw: bytes | bytearray | str) -> str:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    parts: list[str] = []
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            value = payload
        parts.append(str(value))
    return "".join(parts)


def _cleanup_response_text(text: str) -> str:
    cleaned = text.translate(_UNICODE_REPLACEMENTS)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"(?<=\.)(?=\*\*[A-Z])", "\n\n", cleaned)
    cleaned = re.sub(r"(?<=:)(?=\*\*[A-Z])", "\n\n", cleaned)
    cleaned = re.sub(r"([^\n])(?=(#{2,3})\s)", r"\1\n\n", cleaned)
    cleaned = re.sub(r"(?m)^\s*#\s*$\n?", "", cleaned)
    lines: list[str] = []
    for line in cleaned.split("\n"):
        if line.strip() == "**" and lines:
            lines[-1] += "**"
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _invoke_prompt(client, runtime_arn: str, prompt: str, ordinal: int) -> str:
    session_id = f"gdpr-demo-{ordinal:02d}-{uuid.uuid4().hex}"
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        contentType="application/json",
        accept="text/plain",
        runtimeSessionId=session_id,
        runtimeUserId="codex",
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
    )
    raw = response["response"].read()
    return _cleanup_response_text(_parse_sse_text(raw))


def _generate_snapshot(runtime_arn: str, region: str, runtime_name: str) -> dict:
    client = boto3.client("bedrock-agentcore", region_name=region)
    responses: list[dict[str, object]] = []

    for trace in GDPR_AUDITOR_TRACES:
        ordinal = int(trace["ordinal"])
        prompt = str(trace["prompt"])
        print(f"[{ordinal:02d}/50] Invoking {runtime_name}...", flush=True)

        for attempt in range(1, 4):
            try:
                response = _invoke_prompt(client, runtime_arn, prompt, ordinal)
                responses.append({
                    "ordinal": ordinal,
                    "prompt": prompt,
                    "response": response,
                })
                break
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "Unknown")
                if code == "ThrottlingException" and attempt < 3:
                    time.sleep(attempt * 2)
                    continue
                raise

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime_name": runtime_name,
        "runtime_arn": runtime_arn,
        "region": region,
        "query_count": len(responses),
        "responses": responses,
    }


def _format_module(snapshot: dict) -> str:
    meta = {
        "generated_at": snapshot["generated_at"],
        "runtime_name": snapshot["runtime_name"],
        "runtime_arn": snapshot["runtime_arn"],
        "region": snapshot["region"],
        "query_count": snapshot["query_count"],
    }
    meta_json = json.dumps(meta, indent=2, ensure_ascii=True)
    responses_json = json.dumps(snapshot["responses"], indent=2, ensure_ascii=True)

    return (
        '"""Generated live AwsGdprAuditor responses for the AWS GDPR demo golden queries."""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n\n"
        "SNAPSHOT_META = json.loads(\n"
        f"    r'''{meta_json}'''\n"
        ")\n\n"
        "RUNTIME_RESPONSES = json.loads(\n"
        f"    r'''{responses_json}'''\n"
        ")\n\n"
        'RESPONSE_BY_PROMPT = {item["prompt"]: item["response"] for item in RUNTIME_RESPONSES}\n'
    )


def main() -> int:
    args = _parse_args()
    snapshot = _generate_snapshot(args.runtime_arn, args.region, args.runtime_name)
    args.output.write_text(_format_module(snapshot), encoding="utf-8")
    print(f"Wrote snapshot to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
