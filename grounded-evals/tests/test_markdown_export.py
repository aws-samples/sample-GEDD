"""Tests for the markdown error-analysis export."""

from grounded_evals.guide.markdown_export import export_error_analysis_md


def test_empty_storage_produces_valid_md():
    md = export_error_analysis_md({})
    assert md.startswith("# GEDD Error Analysis")
    assert "## Agent Spec" in md
    assert "## Golden Queries" in md
    assert "## Failure Codebook" in md


def test_full_demo_export():
    from grounded_evals.ui.demo_data import (
        DEMO_CODING_ANNOTATIONS,
        DEMO_CODEBOOK,
        DEMO_MEMOS,
        DEMO_PARADIGM_MODEL,
        DEMO_SESSION,
    )

    storage = {
        "session_data": {
            "agent_spec": DEMO_SESSION["agent_spec"],
            "golden_prompts": DEMO_SESSION["golden_prompts"],
        },
        "codebook": DEMO_CODEBOOK,
        "coding_annotations": DEMO_CODING_ANNOTATIONS,
        "memos": DEMO_MEMOS,
        "paradigm_model": DEMO_PARADIGM_MODEL,
        "_generated_judge_prompt": "You are a judge.",
    }
    md = export_error_analysis_md(storage)

    assert "# GEDD Error Analysis — TravelBot" in md
    assert "## Agent Spec" in md
    assert "TravelBot" in md
    assert "## Golden Queries (14 total" in md
    assert "## Failure Codebook" in md
    assert "Policy Hallucination" in md
    assert "## Paradigm Model" in md
    assert "### Phenomenon" in md
    assert "### Causal Conditions" in md
    assert "## Annotated Failures" in md
    assert "## Saturation Evidence" in md
    assert "## Memos" in md
    assert "## Judge Prompt" in md
    assert "You are a judge." in md


def test_50_query_localization_export():
    from grounded_evals.ui.inductive_pm_demo import (
        INDUCTIVE_PM_CODEBOOK,
        INDUCTIVE_PM_CODING_ANNOTATIONS,
        INDUCTIVE_PM_JUDGE_PROMPT,
        INDUCTIVE_PM_MEMOS,
        INDUCTIVE_PM_PARADIGM_MODEL,
        INDUCTIVE_PM_SESSION,
    )

    storage = {
        "session_data": INDUCTIVE_PM_SESSION,
        "codebook": INDUCTIVE_PM_CODEBOOK,
        "coding_annotations": INDUCTIVE_PM_CODING_ANNOTATIONS,
        "memos": INDUCTIVE_PM_MEMOS,
        "paradigm_model": INDUCTIVE_PM_PARADIGM_MODEL,
        "_generated_judge_prompt": INDUCTIVE_PM_JUDGE_PROMPT,
    }
    md = export_error_analysis_md(storage)

    assert "50 total" in md
    assert "## Annotated Failures (50 examples)" in md
    assert "## Judge Prompt" in md
    # Should be token-efficient
    assert len(md) < 60_000


def test_no_paradigm_model():
    storage = {
        "session_data": {"agent_spec": {"name": "X"}, "golden_prompts": []},
        "paradigm_model": {},
        "codebook": [],
        "coding_annotations": [],
        "memos": [],
    }
    md = export_error_analysis_md(storage)
    assert "_No paradigm model built yet._" in md


def test_table_cell_escaping():
    storage = {
        "session_data": {
            "agent_spec": {"name": "Test"},
            "golden_prompts": [
                {
                    "prompt_text": "Query with | pipe and\nnewline",
                    "rationale": "edge",
                    "expected_behavior": "Handle it",
                }
            ],
        },
        "codebook": [],
        "coding_annotations": [],
        "memos": [],
        "paradigm_model": {},
    }
    md = export_error_analysis_md(storage)
    # Pipes and newlines should be escaped in table cells
    assert "\\|" in md
    assert "\n| 1 |" in md
