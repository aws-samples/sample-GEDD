"""Unit tests for judge_builder/ensemble.py — ensemble judging and aggregation."""

import json
from unittest.mock import MagicMock, patch

from grounded_evals.judge_builder.ensemble import (
    EnsembleResult,
    _infer_confidence,
    _parse_judge_response,
    aggregate_ensemble_results,
    ensemble_judge,
)

# ── _parse_judge_response ─────────────────────────────────────────────────────


def test_parse_judge_response_raw_json():
    text = '{"scores": {"accuracy": 4}, "pass": true, "summary": "Good"}'
    result = _parse_judge_response(text)
    assert result["pass"] is True
    assert result["scores"]["accuracy"] == 4


def test_parse_judge_response_json_fence():
    text = 'Here is my evaluation:\n```json\n{"pass": false, "summary": "Bad"}\n```\nDone.'
    result = _parse_judge_response(text)
    assert result["pass"] is False


def test_parse_judge_response_plain_fence():
    text = '```\n{"pass": true}\n```'
    result = _parse_judge_response(text)
    assert result["pass"] is True


def test_parse_judge_response_embedded_json():
    text = 'Analysis: The response is good.\n\n{"scores": {"quality": 5}, "pass": true, "summary": "Excellent"}\n\nEnd.'
    result = _parse_judge_response(text)
    assert result["scores"]["quality"] == 5


def test_parse_judge_response_invalid():
    result = _parse_judge_response("No JSON here at all")
    assert result == {}


def test_parse_judge_response_malformed_json():
    result = _parse_judge_response("{invalid json content}")
    assert result == {}


# ── _infer_confidence ─────────────────────────────────────────────────────────


def test_infer_confidence_unanimous():
    conf, uncertain = _infer_confidence(1.0, 3)
    assert conf == "high"
    assert uncertain is False


def test_infer_confidence_strong_majority():
    conf, uncertain = _infer_confidence(0.9, 5)
    assert conf == "high"
    assert uncertain is False


def test_infer_confidence_medium():
    conf, uncertain = _infer_confidence(0.67, 3)
    assert conf == "medium"
    assert uncertain is False


def test_infer_confidence_low_disagreement():
    conf, uncertain = _infer_confidence(0.5, 4)
    assert conf == "low"
    assert uncertain is True


def test_infer_confidence_single_sample():
    conf, uncertain = _infer_confidence(1.0, 1)
    assert conf == "high"
    assert uncertain is False


# ── ensemble_judge ────────────────────────────────────────────────────────────


def _mock_client_responses(responses: list[str]):
    client = MagicMock()
    side_effects = []
    for text in responses:
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        side_effects.append(msg)
    client.messages.create.side_effect = side_effects
    return client


def test_ensemble_judge_unanimous_pass():
    resp = json.dumps({"scores": {"accuracy": 5}, "pass": True, "summary": "Good"})
    client = _mock_client_responses([resp, resp, resp])
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=3)
    assert result.majority_pass is True
    assert result.pass_votes == 3
    assert result.confidence == "high"
    assert not result.is_uncertain


def test_ensemble_judge_split_vote():
    pass_resp = json.dumps({"scores": {"accuracy": 4}, "pass": True, "summary": "OK"})
    fail_resp = json.dumps({"scores": {"accuracy": 2}, "pass": False, "summary": "Bad"})
    client = _mock_client_responses([pass_resp, fail_resp, pass_resp])
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=3)
    assert result.pass_votes == 2
    assert result.fail_votes == 1
    assert result.majority_pass is True


def test_ensemble_judge_all_fail():
    resp = json.dumps({"scores": {"safety": 1}, "pass": False, "summary": "Dangerous"})
    client = _mock_client_responses([resp, resp])
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=2)
    assert result.majority_pass is False
    assert result.fail_votes == 2


def test_ensemble_judge_all_errors():
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("API down")
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=2)
    assert result.error != ""
    assert "failed" in result.error


def test_ensemble_judge_median_scores():
    responses = [
        json.dumps({"scores": {"accuracy": 3, "tone": 4}, "pass": True, "summary": ""}),
        json.dumps({"scores": {"accuracy": 5, "tone": 4}, "pass": True, "summary": ""}),
        json.dumps({"scores": {"accuracy": 4, "tone": 2}, "pass": True, "summary": ""}),
    ]
    client = _mock_client_responses(responses)
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=3)
    assert result.median_scores["accuracy"] == 4  # median of [3, 5, 4]
    assert result.median_scores["tone"] == 4  # median of [4, 4, 2]


# ── aggregate_ensemble_results ────────────────────────────────────────────────


def test_aggregate_empty():
    assert aggregate_ensemble_results([]) == {}


def test_aggregate_basic():
    results = [
        EnsembleResult(
            query="q1",
            response="r1",
            n_samples=3,
            pass_votes=3,
            fail_votes=0,
            majority_pass=True,
            pass_fraction=1.0,
            confidence="high",
            is_uncertain=False,
            median_scores={"accuracy": 4.0},
        ),
        EnsembleResult(
            query="q2",
            response="r2",
            n_samples=3,
            pass_votes=1,
            fail_votes=2,
            majority_pass=False,
            pass_fraction=0.33,
            confidence="low",
            is_uncertain=True,
            median_scores={"accuracy": 2.0},
        ),
    ]
    report = aggregate_ensemble_results(results)
    assert report["total_evaluated"] == 2
    assert report["pass_count"] == 1
    assert report["fail_count"] == 1
    assert report["uncertain_count"] == 1
    assert report["avg_criterion_scores"]["accuracy"] == 3.0
    assert report["confidence_distribution"]["high"] == 1
    assert report["confidence_distribution"]["low"] == 1
