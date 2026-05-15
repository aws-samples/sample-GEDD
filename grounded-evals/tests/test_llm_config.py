import os
from pathlib import Path
from unittest.mock import patch

from grounded_evals.llm.client import LLMConfig


def test_config_from_env_anthropic():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
        cfg = LLMConfig.from_env()
        assert cfg.provider == "anthropic"
        assert cfg.api_key == "sk-ant-test"


def test_config_from_env_bedrock():
    with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}, clear=True):
        cfg = LLMConfig.from_env()
        assert cfg.provider == "bedrock"
        assert cfg.region == "us-west-2"
        assert "claude" in cfg.model_id


def test_config_from_env_default_region():
    with patch.dict(os.environ, {}, clear=True):
        cfg = LLMConfig.from_env()
        assert cfg.provider == "bedrock"
        assert cfg.region == "us-east-1"


def test_config_from_yaml(tmp_path: Path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(
        "llm:\n"
        "  provider: bedrock\n"
        "  region: eu-west-1\n"
        "  model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0\n"
    )
    cfg = LLMConfig.from_yaml(config_file)
    assert cfg.provider == "bedrock"
    assert cfg.region == "eu-west-1"


def test_config_from_yaml_missing_file():
    with patch.dict(os.environ, {}, clear=True):
        cfg = LLMConfig.from_yaml("/nonexistent/path.yaml")
        assert cfg.provider == "bedrock"
