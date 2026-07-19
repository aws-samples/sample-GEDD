from __future__ import annotations

from uuid import uuid4

from grounded_evals.agent.tools import StateBundle
from grounded_evals.ears.baseline import BaselineGenerator
from grounded_evals.ears.measurement import MeasurementEngine
from grounded_evals.ears.parser import EARSParser
from grounded_evals.ears.transformer import CodeMetrics, EARSTransformer
from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import Capability
from grounded_evals.models.core import Code, CodeType, GoldenPrompt


def _session_with_failure_code() -> Session:
    session = Session()
    session.update_agent(
        name="TestBot",
        description="Support assistant",
        system_prompt="You help support users.",
    )
    session.agent_spec.capabilities = [Capability(name="Refund lookup")]
    code = Code(
        label="Missing Refund Policy",
        code_type=CodeType.DESCRIPTIVE,
        definition="Agent omits required refund policy detail.",
    )
    session.codes = [code]
    session.golden_prompts = [
        GoldenPrompt(
            prompt_text="Can I get a refund?",
            category_id=uuid4(),
            code_id=code.id,
            rationale="edge_case",
            expected_behavior="State the refund policy.",
        )
    ]
    return session


def test_ears_transformer_parser_and_measurement_round_trip() -> None:
    session = _session_with_failure_code()
    metrics = {
        session.codes[0].id: CodeMetrics(
            severity=4,
            frequency=2,
            dimension="completeness",
        )
    }

    gedd_doc = EARSTransformer().transform(session, metrics, paradigm=None)
    markdown = EARSParser().judge_spec_md(gedd_doc)
    parsed = EARSParser().parse(markdown)
    baseline = BaselineGenerator().generate(session.agent_spec)
    report = MeasurementEngine().measure(baseline, parsed, session)

    assert markdown.startswith("# Requirements Document")
    assert "## Requirements" in markdown
    assert "### Requirement 1:" in markdown
    assert "**User Story:**" in markdown
    assert "#### Acceptance Criteria" in markdown
    assert "WHEN TestBot produces a candidate customer-facing response" in markdown
    assert (
        "THE JUDGE SHALL classify the response as a release-blocking domain failure"
        in markdown
    )
    assert "LLM-as-Judge Release Gate" in markdown
    assert "pass_fail, failure_code, severity, rationale" in markdown
    assert "customer_visible_block" in markdown
    assert parsed.requirements[0].traceability_links
    assert "Missing Refund Policy" in markdown
    assert report.gedd_metrics.domain_coverage == 100.0
    assert report.overall_improvement > 0


def test_legacy_ears_markdown_still_parses() -> None:
    session = _session_with_failure_code()
    metrics = {session.codes[0].id: CodeMetrics(severity=4, frequency=2)}

    gedd_doc = EARSTransformer().transform(session, metrics, paradigm=None)
    markdown = EARSParser().pretty_print(gedd_doc)
    parsed = EARSParser().parse(markdown)

    assert parsed.requirements
    assert parsed.requirements[0].traceability_links


def test_state_bundle_import_does_not_trigger_missing_ears_modules() -> None:
    state = StateBundle(session=_session_with_failure_code(), current_step=5)

    assert state.session.generate_ears_requirements().requirements
