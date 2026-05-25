"""Unit tests for judge_builder/constitutional.py — constitutional evaluation."""

import json
from unittest.mock import MagicMock

from grounded_evals.judge_builder.constitutional import (
    ConstitutionalPrinciple,
    build_constitutional_judge_prompt,
    build_constitutional_principles,
    constitutional_judge,
    _format_principles_block,
)


def _make_codebook():
    return [
        {"name": "hallucination", "definition": "Agent invents facts"},
        {"name": "tone_collapse", "definition": "Agent becomes rude under pressure"},
    ]


def _make_paradigm():
    return {
        "phenomenon": "Agent failure modes",
        "causal_conditions": ["Ambiguous query", "Missing context"],
        "strategies": ["Fabrication", "Deflection"],
        "consequences": ["User distrust"],
        "context": ["Long conversations"],
    }


def _make_annotations():
    return [
        {
            "query": "What's the refund policy?",
            "response": "Our refund policy allows returns within 90 days.",
            "codes": ["hallucination"],
            "severity": "critical",
            "confidence": "high",
            "memo": "No such policy exists",
        },
        {
            "query": "I'm frustrated!",
            "response": "That's not my problem.",
            "codes": ["tone_collapse"],
            "severity": "functional",
            "confidence": "medium",
            "memo": "Rude response",
        },
    ]


# ── build_constitutional_principles ──────────────────────────────────────────

def test_build_principles_basic():
    principles = build_constitutional_principles(
        _make_codebook(), _make_paradigm(), _make_annotations()
    )
    assert len(principles) == 2
    assert principles[0].code_name == "hallucination"
    assert "Ambiguous query" in principles[0].causal_trigger


def test_build_principles_with_error_mappings():
    mappings = [
        {"error_code": "hallucination", "primary_category": "accuracy"},
        {"error_code": "tone_collapse", "primary_category": "tone"},
    ]
    principles = build_constitutional_principles(
        _make_codebook(), _make_paradigm(), _make_annotations(), mappings
    )
    assert principles[0].dimension == "accuracy"
    assert principles[1].dimension == "tone"


def test_build_principles_empty_codebook():
    principles = build_constitutional_principles([], {}, [])
    assert principles == []


def test_build_principles_no_annotations():
    principles = build_constitutional_principles(
        _make_codebook(), _make_paradigm(), []
    )
    assert len(principles) == 2
    assert "No example available" in principles[0].discriminating_example


def test_build_principles_picks_highest_severity_example():
    annotations = [
        {"query": "q1", "response": "r1", "codes": ["hallucination"],
         "severity": "cosmetic", "confidence": "low", "memo": ""},
        {"query": "q2", "response": "r2", "codes": ["hallucination"],
         "severity": "catastrophic", "confidence": "high", "memo": "worst case"},
    ]
    principles = build_constitutional_principles(
        [{"name": "hallucination", "definition": "x"}], {}, annotations
    )
    assert "q2" in principles[0].discriminating_example


# ── _format_principles_block ──────────────────────────────────────────────────

def test_format_principles_block():
    principles = [
        ConstitutionalPrinciple(
            code_name="hallucination",
            definition="Agent invents facts",
            causal_trigger="Missing context",
            discriminating_example="Example text",
            dimension="accuracy",
        )
    ]
    block = _format_principles_block(principles)
    assert "NO HALLUCINATION" in block
    assert "[Accuracy]" in block
    assert "Missing context" in block


# ── constitutional_judge ──────────────────────────────────────────────────────

def test_constitutional_judge_success():
    verdict_json = json.dumps({
        "principle_verdicts": [
            {"code": "hallucination", "reasoning": "No facts invented", "violated": False, "severity": None}
        ],
        "violated_codes": [],
        "overall_pass": True,
        "confidence": "high",
        "summary": "Response is clean.",
    })
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=verdict_json)]
    client.messages.create.return_value = msg

    principles = [ConstitutionalPrinciple(
        code_name="hallucination", definition="x",
        causal_trigger="y", discriminating_example="z",
    )]
    result = constitutional_judge("Hello", "Hi there!", principles, client=client, model_id="test")
    assert result.overall_pass is True
    assert result.violated_codes == []
    assert result.confidence == "high"


def test_constitutional_judge_violation_detected():
    verdict_json = json.dumps({
        "principle_verdicts": [
            {"code": "hallucination", "reasoning": "Invented policy", "violated": True, "severity": "critical"}
        ],
        "violated_codes": ["hallucination"],
        "overall_pass": False,
        "confidence": "high",
        "summary": "Hallucination detected.",
    })
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=verdict_json)]
    client.messages.create.return_value = msg

    principles = [ConstitutionalPrinciple(
        code_name="hallucination", definition="x",
        causal_trigger="y", discriminating_example="z",
    )]
    result = constitutional_judge("Policy?", "30 day refund", principles, client=client, model_id="test")
    assert result.overall_pass is False
    assert "hallucination" in result.violated_codes


def test_constitutional_judge_parse_error():
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text="This is not JSON at all")]
    client.messages.create.return_value = msg

    principles = [ConstitutionalPrinciple(
        code_name="x", definition="x", causal_trigger="x", discriminating_example="x",
    )]
    result = constitutional_judge("q", "r", principles, client=client, model_id="test")
    assert result.overall_pass is False
    assert "Parse error" in result.summary


# ── build_constitutional_judge_prompt ─────────────────────────────────────────

def test_build_constitutional_judge_prompt():
    principles = [
        ConstitutionalPrinciple(
            code_name="safety_violation", definition="Harmful content",
            causal_trigger="Jailbreak attempt", discriminating_example="Example",
            dimension="safety",
        )
    ]
    prompt = build_constitutional_judge_prompt(principles, "TestBot", "A test agent")
    assert "TestBot" in prompt
    assert "NO SAFETY_VIOLATION" in prompt
    assert "{query}" in prompt
    assert "{response}" in prompt
