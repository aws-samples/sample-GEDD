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


def test_main_nav_keeps_ai_pm_flow_as_top_level_tabs():
    from grounded_evals.ui.layout import NAV_ITEMS

    labels = [item["label"] for item in NAV_ITEMS]
    paths = [item["path"] for item in NAV_ITEMS]

    assert labels == ["Home", "AI PM Coach", "PM Workbench", "Judge", "Report"]
    assert paths == ["/", "/coach", "/coding", "/judge", "/report"]
    assert "Demos" not in labels
    assert all("children" not in item for item in NAV_ITEMS)
    assert next(item for item in NAV_ITEMS if item["label"] == "PM Workbench")["primary"] is True


def test_ai_pm_progress_rail_uses_coach_to_judge_flow():
    from grounded_evals.ui import layout

    storage = {
        "session_data": {
            "agent_spec": {"name": "ProducerGate"},
            "golden_prompts": [{"prompt_text": "q1"}],
        },
        "coding_annotations": [{"codes": ["Feature Promise Hallucination"]}],
    }
    with patch.object(layout, "app", _make_mock_app(storage)):
        steps = layout._get_progress_state()

    assert [step["path"] for step in steps] == ["/coach", "/coding", "/judge", "/report"]
    assert [step["label"] for step in steps] == [
        "Coach",
        "PM Workbench",
        "Judge",
        "Report",
    ]


def test_clear_project_state_preserves_login_and_removes_demo_state():
    from grounded_evals.ui.layout import _clear_project_state

    storage = {
        "authenticated": True,
        "email": "pm@example.com",
        "oauth_tokens": {"access_token": "token"},
        "session_data": {"agent_spec": {"name": "DemoBot"}},
        "annotations": [{"query": "q"}],
        "codebook": [{"name": "Failure"}],
        "coding_annotations": [{"codes": ["Failure"]}],
        "demo_methodology": {"synthetic_query_count": 50},
        "eval_history": [{"run": 1}],
        "_judge_mappings": [{"code": "Failure"}],
        "_generated_judge_prompt": "judge prompt",
    }

    _clear_project_state(storage)

    assert storage == {
        "authenticated": True,
        "email": "pm@example.com",
        "oauth_tokens": {"access_token": "token"},
    }


def test_get_progress_empty_storage():
    from grounded_evals.ui.home_page import _get_progress

    progress = _get_progress({})
    assert progress["/coach"] == "todo"
    assert progress["/coding"] == "todo"


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
    assert progress["/coding"] == "current"


def test_get_progress_full_pipeline():
    from grounded_evals.ui.home_page import _get_progress

    storage = {
        "session_data": {
            "agent_spec": {"name": "Bot", "system_prompt": "Answer questions."},
            "golden_prompts": [{"prompt_text": "q1"}],
        },
        "eval_results": [{"query": "q1", "responses": {}, "annotations": {}}],
        "coding_annotations": [{"codes": ["hallucination"]}],
        "_generated_judge_prompt": "judge prompt",
    }
    progress = _get_progress(storage)
    assert progress["/coach"] == "done"
    assert progress["/coding"] == "done"
    assert progress["/judge"] == "done"


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

    assert len(domains) >= 21
    assert {
        "PM Annotation Workbench",
        "AAA Game Producer",
        "AAA Game Operator",
        "RxBot",
        "TaxBot",
        "MigrateBot",
        "EnergyBot",
    }.issubset(names)


def test_home_expert_discoveries_are_domain_specific():
    from grounded_evals.ui.home_page import EXPERT_DISCOVERIES

    codes = {item["error_code"] for item in EXPERT_DISCOVERIES}
    featured = EXPERT_DISCOVERIES[:3]

    assert len(EXPERT_DISCOVERIES) == 5
    assert {
        "dosage_unit_confusion",
        "coverage_hallucination",
        "incomplete_guidance",
        "bar_misapplication",
        "consent_bypass_for_targeting",
    } == codes
    assert {item["demo_id"] for item in featured} == {"rx", "insure", "tax"}
    assert all(item["prompt"] and item["unsafe_answer"] and item["gate"] for item in featured)


def test_inductive_pm_demo_loads_50_query_workbench():
    from grounded_evals.ui.inductive_pm_demo import load_inductive_pm_demo

    storage = {"authenticated": True, "email": "pm@example.com"}
    load_inductive_pm_demo(storage)

    session = storage["session_data"]
    methodology = storage["demo_methodology"]

    assert session["agent_spec"]["name"] == "PlayerReady PM Workbench"
    assert len(session["golden_prompts"]) == 50
    assert len(storage["annotations"]) == 50
    assert len(storage["coding_annotations"]) == 50
    assert len(storage["codebook"]) == 10
    assert methodology["synthetic_query_count"] == 50
    assert methodology["open_code_count"] == 10
    assert methodology["saturation_window"] == 8
    assert methodology["new_codes_in_final_window"] == 0
    assert "open coding" in storage["_generated_judge_prompt"].lower()


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


def test_judge_prompt_inputs_require_annotated_failure_code():
    from grounded_evals.ui.coding_page import (
        _failure_mode_count_for_judge,
        _has_judge_prompt_inputs,
    )

    empty = {"coding_annotations": [], "codebook": [{"name": "Unused"}]}
    assert _failure_mode_count_for_judge(empty) == 1
    assert _has_judge_prompt_inputs(empty) is False

    annotation_without_code = {
        "coding_annotations": [{"codes": [], "memo": "Bad answer"}],
        "codebook": [{"name": "Unused"}],
    }
    assert _has_judge_prompt_inputs(annotation_without_code) is False

    storage = {
        "coding_annotations": [{"codes": ["Missed escalation"], "severity": "critical"}],
        "codebook": [{"name": "Missed escalation"}, {"name": ""}],
    }
    assert _failure_mode_count_for_judge(storage) == 1
    assert _has_judge_prompt_inputs(storage) is True


def test_store_judge_prompt_marks_core_flow_complete():
    from grounded_evals.ui.coding_page import _store_judge_prompt

    storage = {"current_step": 4}
    _store_judge_prompt(storage, "judge prompt")

    assert storage["_simple_judge_prompt"] == "judge prompt"
    assert storage["_generated_judge_prompt"] == "judge prompt"
    assert storage["current_step"] == 5
    assert storage["_jb_generated_at"]


def test_annotation_export_payload_includes_judge_input_artifacts():
    from grounded_evals.ui.coding_page import _agent_export_slug, _annotation_export_payload

    storage = {
        "session_data": {
            "agent_spec": {
                "name": "Producer Gate",
                "description": "Launch companion",
            }
        },
        "codebook": [{"name": "Feature Promise Hallucination"}],
        "coding_annotations": [
            {
                "query": "Will it ship at 60 FPS?",
                "response": "Yes",
                "codes": ["Feature Promise Hallucination"],
            }
        ],
        "memos": [{"text": "Public launch promise without source of truth"}],
        "_generated_judge_prompt": "judge prompt",
        "_jb_generated_at": "2026-06-10T12:00:00",
    }

    payload = _annotation_export_payload(
        storage,
        failure_modes=[{"name": "Feature Promise Hallucination"}],
    )

    assert _agent_export_slug(storage) == "producer_gate"
    assert payload["artifact"] == "gedd_error_analysis_annotations"
    assert payload["source"]["created_from"] == "pm_annotations"
    assert payload["source"]["annotation_count"] == 1
    assert payload["source"]["failure_mode_count"] == 1
    assert payload["coding_annotations"][0]["query"] == "Will it ship at 60 FPS?"
    assert payload["judge_prompt"]["text"] == "judge prompt"
    assert payload["failure_modes"][0]["name"] == "Feature Promise Hallucination"


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
