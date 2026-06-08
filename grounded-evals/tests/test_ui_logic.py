"""Unit tests for pure UI-layer logic functions that don't require a running browser."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ── _build_failure_patterns (report_page) ────────────────────────────────────


def test_build_failure_patterns_empty():
    from grounded_evals.ui.report_page import _build_failure_patterns

    assert _build_failure_patterns([], []) == []


def test_build_failure_patterns_no_annotations():
    from grounded_evals.ui.report_page import _build_failure_patterns

    codebook = [{"name": "hallucination", "definition": "made up fact"}]
    assert _build_failure_patterns(codebook, []) == []


def test_build_failure_patterns_counts_and_severity():
    from grounded_evals.ui.report_page import _build_failure_patterns

    codebook = [
        {"name": "hallucination", "definition": "made up"},
        {"name": "wrong_tone", "definition": "rude"},
        {"name": "incomplete", "definition": "missing info"},
    ]
    coding_annotations = [
        {"codes": ["hallucination", "wrong_tone"]},
        {"codes": ["hallucination"]},
        {"codes": ["hallucination"]},
        {"codes": ["incomplete"]},
        {"codes": ["hallucination"]},
    ]
    patterns = _build_failure_patterns(codebook, coding_annotations)
    names = [p["name"] for p in patterns]
    # hallucination appears 4 times → should be first (sorted desc)
    assert names[0] == "hallucination"
    # zero-frequency codes are excluded
    assert all(p["frequency"] > 0 for p in patterns)
    # severity thresholds: ≥40% → high, ≥20% → medium, else low
    total_codes = 4 + 1 + 1  # hallucination=4, wrong_tone=1, incomplete=1
    for p in patterns:
        pct = p["frequency"] / total_codes
        expected = "high" if pct >= 0.4 else ("medium" if pct >= 0.2 else "low")
        assert p["severity"] == expected


def test_build_failure_patterns_sorted_desc():
    from grounded_evals.ui.report_page import _build_failure_patterns

    codebook = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    annotations = [
        {"codes": ["c", "c", "c"]},
        {"codes": ["b", "b"]},
        {"codes": ["a"]},
    ]
    patterns = _build_failure_patterns(codebook, annotations)
    freqs = [p["frequency"] for p in patterns]
    assert freqs == sorted(freqs, reverse=True)


# ── _is_similar (coding_page) ─────────────────────────────────────────────────


def test_is_similar_identical():
    from grounded_evals.ui.coding_page import _is_similar

    assert _is_similar("hallucinated price", "hallucinated price") is True


def test_is_similar_close_strings():
    from grounded_evals.ui.coding_page import _is_similar

    # Same root words, minor variation
    assert _is_similar("wrong tone response", "wrong tone in response") is True


def test_is_similar_unrelated():
    from grounded_evals.ui.coding_page import _is_similar

    assert _is_similar("hallucination error", "missing context") is False


def test_is_similar_empty():
    from grounded_evals.ui.coding_page import _is_similar

    assert _is_similar("", "hallucination") is False
    assert _is_similar("hallucination", "") is False


def test_is_similar_near_duplicate_codes():
    from grounded_evals.ui.coding_page import _is_similar

    # These share enough n-grams / words to be considered similar
    assert _is_similar("fabricated entity", "fabricated entities") is True


# ── _get_progress (home_page) ─────────────────────────────────────────────────


def test_get_progress_empty_storage():
    from grounded_evals.ui.home_page import _get_progress

    progress = _get_progress({})
    assert progress["/coach"] == "todo"
    assert progress["/eval"] == "todo"


def test_get_progress_coach_done():
    from grounded_evals.ui.home_page import _get_progress

    storage = {
        "session_data": {
            "agent_spec": {"name": "TestBot", "system_prompt": "Be helpful."},
            "golden_prompts": [{"prompt_text": "Hello"}],
        }
    }
    progress = _get_progress(storage)
    assert progress["/coach"] == "done"
    assert progress["/eval"] == "current"


def test_get_progress_full_pipeline():
    from grounded_evals.ui.home_page import _get_progress

    storage = {
        "session_data": {
            "agent_spec": {"name": "Bot", "system_prompt": "Answer questions."},
            "golden_prompts": [{"prompt_text": "q1"}],
        },
        "eval_results": [{"query": "q1", "responses": {}, "annotations": {}}],
        "coding_annotations": [{"codes": ["hallucination"]}],
        "paradigm_model": {"phenomenon": ["hallucination"]},
    }
    progress = _get_progress(storage)
    assert progress["/coach"] == "done"
    assert progress["/eval"] == "done"
    assert progress["/coding"] == "done"
    assert progress["/analysis"] == "done"


def test_get_progress_no_agent_name():
    from grounded_evals.ui.home_page import _get_progress

    storage = {"session_data": {"agent_spec": {"name": "", "system_prompt": "x"}}}
    progress = _get_progress(storage)
    assert progress["/coach"] == "todo"


def test_home_empty_session_has_no_content():
    from grounded_evals.ui.home_page import _has_session_content

    assert _has_session_content({}) is False
    assert _has_session_content({"session_data": {"agent_spec": {}, "golden_prompts": []}}) is False


def test_home_detects_loaded_session_content():
    from grounded_evals.ui.home_page import _has_session_content

    assert _has_session_content({"session_data": {"agent_spec": {"name": "RxBot"}}}) is True
    assert (
        _has_session_content({"session_data": {"golden_prompts": [{"prompt_text": "q"}]}}) is True
    )
    assert (
        _has_session_content({"coding_annotations": [{"codes": ["dosage_unit_confusion"]}]}) is True
    )


def test_domain_registry_includes_all_launch_demos():
    from grounded_evals.ui.demos_page import _build_domain_registry

    domains = _build_domain_registry()
    names = {d["name"] for d in domains}

    assert len(domains) == 18
    assert {"RxBot", "TaxBot", "MigrateBot", "EnergyBot"}.issubset(names)


def test_home_expert_discoveries_are_domain_specific():
    from grounded_evals.ui.home_page import EXPERT_DISCOVERIES

    codes = {item["error_code"] for item in EXPERT_DISCOVERIES}

    assert len(EXPERT_DISCOVERIES) == 5
    assert {
        "dosage_unit_confusion",
        "coverage_hallucination",
        "incomplete_guidance",
        "bar_misapplication",
        "consent_bypass_for_targeting",
    } == codes


# ── _build_responses (coding_page) ───────────────────────────────────────────


def test_build_responses_empty():
    from grounded_evals.ui.coding_page import _build_responses

    assert _build_responses({}) == []


def test_build_responses_from_annotations():
    from grounded_evals.ui.coding_page import _build_responses

    storage = {
        "annotations": [
            {"query": "q1", "response": "r1", "annotation": "correct", "model": "m1"},
        ]
    }
    results = _build_responses(storage)
    assert len(results) == 1
    assert results[0]["query"] == "q1"


def test_build_responses_deduplicates():
    from grounded_evals.ui.coding_page import _build_responses

    storage = {
        "annotations": [
            {"query": "q1", "response": "r1", "annotation": "correct", "model": "m1"},
        ],
        "eval_results": [
            {
                "query": "q1",
                "responses": {"m1": "r1"},
                "annotations": {"m1": "correct"},
                "notes": "",
            },
        ],
    }
    results = _build_responses(storage)
    # Same (query, response) pair appears in both → deduplicated
    assert len(results) == 1


def test_build_responses_merges_eval_results():
    from grounded_evals.ui.coding_page import _build_responses

    storage = {
        "eval_results": [
            {
                "query": "q2",
                "responses": {"model-a": "response text", "model-b": "other text"},
                "annotations": {},
                "notes": "",
            }
        ]
    }
    results = _build_responses(storage)
    assert len(results) == 2
    queries = {r["query"] for r in results}
    assert queries == {"q2"}


def test_build_responses_skips_errors():
    from grounded_evals.ui.coding_page import _build_responses

    storage = {
        "eval_results": [
            {
                "query": "q3",
                "responses": {"m": "[Error: timeout]"},
                "annotations": {},
                "notes": "",
            }
        ]
    }
    assert _build_responses(storage) == []


# ── _label_css_color and _get_all_labels (eval_tab) ──────────────────────────


def _make_mock_app(storage_dict: dict):
    """Return a mock app whose storage.user behaves like a plain dict."""
    from unittest.mock import MagicMock

    mock_app = MagicMock()
    mock_app.storage.user = storage_dict
    return mock_app


def test_get_all_labels_defaults_only():
    from grounded_evals.ui import eval_tab

    with patch.object(eval_tab, "app", _make_mock_app({})):
        labels = eval_tab._get_all_labels()
    assert len(labels) == len(eval_tab.DEFAULT_LABELS)
    keys = {l["key"] for l in labels}
    assert "correct" in keys
    assert "partial" in keys
    assert "incorrect" in keys


def test_get_all_labels_with_custom():
    from grounded_evals.ui import eval_tab

    custom = [{"key": "tone_issue", "label": "Tone Issue", "color": "purple"}]
    with patch.object(eval_tab, "app", _make_mock_app({"custom_annotation_labels": custom})):
        labels = eval_tab._get_all_labels()
    assert len(labels) == len(eval_tab.DEFAULT_LABELS) + 1
    assert labels[-1]["key"] == "tone_issue"


def test_label_css_color_defaults():
    from grounded_evals.ui import eval_tab

    with patch.object(eval_tab, "app", _make_mock_app({})):
        assert eval_tab._label_css_color("correct") == eval_tab.LABEL_COLORS["green"]
        assert eval_tab._label_css_color("partial") == eval_tab.LABEL_COLORS["orange"]
        assert eval_tab._label_css_color("incorrect") == eval_tab.LABEL_COLORS["red"]


def test_label_css_color_unknown_returns_default():
    from grounded_evals.ui import eval_tab

    with patch.object(eval_tab, "app", _make_mock_app({})):
        color = eval_tab._label_css_color("nonexistent_key")
    assert color == "var(--border-default)"


def test_label_css_color_custom_label():
    from grounded_evals.ui import eval_tab

    custom = [{"key": "my_label", "label": "My Label", "color": "purple"}]
    with patch.object(eval_tab, "app", _make_mock_app({"custom_annotation_labels": custom})):
        color = eval_tab._label_css_color("my_label")
    assert color == eval_tab.LABEL_COLORS["purple"]
