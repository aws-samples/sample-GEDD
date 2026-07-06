"""Export GEDD session state as the SME error-analysis handoff document."""

from __future__ import annotations

from datetime import UTC, datetime


def export_error_analysis_md(storage: dict) -> str:
    """Convert user storage state into SME_error_analysis.md for Kiro Power consumption."""
    session = storage.get("session_data") or {}
    agent = session.get("agent_spec", {}) if isinstance(session, dict) else {}
    if not isinstance(agent, dict):
        agent = {}

    agent_name = agent.get("name", "Agent")
    agent_desc = agent.get("description", "")
    domain_context = agent.get("domain_context", "")
    known_edge_cases = agent.get("known_edge_cases", [])
    constraints = agent.get("constraints", [])
    system_prompt = agent.get("system_prompt", "")
    golden_prompts = session.get("golden_prompts", [])
    codebook = storage.get("codebook", [])
    coding_annotations = storage.get("coding_annotations", [])
    memos = storage.get("memos", [])
    paradigm_model = storage.get("paradigm_model", {})
    baseline_requirements = storage.get("baseline_requirements_md", "")
    baseline_filename = storage.get("baseline_requirements_filename", "requirements.md")

    # Compute stats
    total = len(coding_annotations)
    correct = sum(1 for a in coding_annotations if _verdict(a) == "correct")
    partial = sum(1 for a in coding_annotations if _verdict(a) == "partial")
    incorrect = sum(1 for a in coding_annotations if _verdict(a) == "incorrect")

    # Saturation
    categories: dict[str, int] = {}
    for p in golden_prompts:
        cat = p.get("rationale", "uncategorized") if isinstance(p, dict) else "uncategorized"
        categories[cat] = categories.get(cat, 0) + 1
    saturated = sum(1 for n in categories.values() if n >= 3)
    sat_pct = int(saturated / len(categories) * 100) if categories else 0

    lines: list[str] = []
    lines.append(f"# SME Error Analysis — {agent_name}\n")
    lines.append(f"Exported: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n")
    lines.append("## Handoff Purpose\n")
    lines.append(
        "`SME_error_analysis.md` is the domain-expert-curated evidence file. "
        "Use it to build or improve Kiro `requirements.md` and to generate the "
        "LLM-as-a-Judge release gate from the same failure evidence.\n"
    )

    # Domain profile and agent spec
    lines.append("## Domain Expert Profile\n")
    if domain_context:
        lines.append(f"- **Domain Context:** {domain_context}")
    lines.append(f"- **Name:** {agent_name}")
    lines.append(f"- **Description:** {agent_desc}")
    if agent.get("capabilities"):
        caps = ", ".join(
            c["name"] if isinstance(c, dict) else str(c)
            for c in agent["capabilities"]
        )
        lines.append(f"- **Capabilities:** {caps}")
    if agent.get("target_users"):
        users = ", ".join(
            u["name"] if isinstance(u, dict) else str(u)
            for u in agent["target_users"]
        )
        lines.append(f"- **Target Users:** {users}")
    if known_edge_cases:
        edge_cases = ", ".join(str(item) for item in known_edge_cases)
        lines.append(f"- **Known Edge Cases:** {edge_cases}")
    if constraints:
        hard_rules = ", ".join(str(item) for item in constraints)
        lines.append(f"- **Constraints:** {hard_rules}")
    if system_prompt:
        preview = system_prompt[:500] + ("..." if len(system_prompt) > 500 else "")
        lines.append(f"\n### System Prompt\n\n```\n{preview}\n```\n")

    # Existing Kiro baseline requirements
    if baseline_requirements.strip():
        lines.append("## Baseline Kiro Requirements\n")
        lines.append(f"- **Filename:** {baseline_filename}")
        uploaded_at = storage.get("baseline_requirements_uploaded_at", "")
        if uploaded_at:
            lines.append(f"- **Uploaded At:** {uploaded_at}")
        lines.append("\n````markdown")
        lines.append(baseline_requirements.strip())
        lines.append("````\n")

    # Curated domain queries
    lines.append(f"## Curated Domain Queries ({len(golden_prompts)} total, {sat_pct}% saturated)\n")
    if golden_prompts:
        lines.append("| # | Query | Category | Expected Behavior |")
        lines.append("|---|-------|----------|-------------------|")
        for i, p in enumerate(golden_prompts, 1):
            if not isinstance(p, dict):
                continue
            q = _cell(p.get("prompt_text", ""))
            cat = p.get("rationale", "")
            exp = _cell(p.get("expected_behavior", ""))
            lines.append(f"| {i} | {q} | {cat} | {exp} |")
    lines.append("")

    # Annotations Summary
    lines.append("## Annotations Summary\n")
    lines.append(
        f"- **Total:** {total} | Correct: {correct}"
        f" | Partial: {partial} | Incorrect: {incorrect}"
    )
    models = {a.get("model", "") for a in coding_annotations if a.get("model")}
    if models:
        lines.append(f"- **Models tested:** {', '.join(sorted(models))}")
    lines.append("")

    # Failure Codebook
    lines.append("## Failure Codebook\n")
    if codebook:
        lines.append("| Code | Severity | Freq | Definition |")
        lines.append("|------|----------|------|------------|")
        freq = _code_frequencies(coding_annotations)
        for code in codebook:
            if not isinstance(code, dict):
                continue
            name = code.get("name", "")
            sev = _code_severity(name, coding_annotations)
            f = freq.get(name, 0)
            defn = _cell(code.get("definition", ""))
            lines.append(f"| {name} | {sev} | {f} | {defn} |")
    else:
        lines.append("_No failure codes defined yet._")
    lines.append("")

    # Paradigm Model
    lines.append("## Paradigm Model\n")
    if paradigm_model and any(
        paradigm_model.get(k)
        for k in ("phenomenon", "causal_conditions", "context",
                  "intervening_conditions", "strategies", "consequences")
    ):
        phenomenon = paradigm_model.get("phenomenon", [])
        if phenomenon:
            lines.append(f"### Phenomenon\n\n{_list_items(phenomenon)}\n")
        for key, label in [
            ("causal_conditions", "Causal Conditions"),
            ("context", "Context"),
            ("intervening_conditions", "Intervening Conditions"),
            ("strategies", "Action Strategies"),
            ("consequences", "Consequences"),
        ]:
            items = paradigm_model.get(key, [])
            if items:
                lines.append(f"### {label}\n\n{_list_items(items)}\n")
    else:
        lines.append("_No paradigm model built yet._\n")

    # Annotated Examples (failures only)
    failures = [a for a in coding_annotations if _verdict(a) in ("partial", "incorrect")]
    if failures:
        lines.append(f"## Annotated Failures ({len(failures)} examples)\n")
        for i, ann in enumerate(failures, 1):
            verdict = _verdict(ann)
            lines.append(f"### Example {i} [{verdict}]\n")
            lines.append(f"**Query:** {ann.get('query', '')}\n")
            resp = ann.get("response", "")
            if len(resp) > 400:
                resp = resp[:400] + "..."
            lines.append(f"**Response:** {resp}\n")
            codes = ann.get("codes", [])
            if isinstance(codes, str):
                codes = [codes]
            if codes:
                lines.append(f"**Codes:** {', '.join(codes)}")
            sev = ann.get("severity", "")
            conf = ann.get("confidence", "")
            if sev or conf:
                parts = []
                if sev:
                    parts.append(f"Severity: {sev}")
                if conf:
                    parts.append(f"Confidence: {conf}")
                lines.append(f"**{' | '.join(parts)}**")
            memo = ann.get("memo", "")
            if memo:
                lines.append(f"**Memo:** {memo}")
            lines.append("")

    # Saturation Evidence
    lines.append("## Saturation Evidence\n")
    if categories:
        lines.append("| Category | Queries | Status |")
        lines.append("|----------|---------|--------|")
        for cat, n in sorted(categories.items(), key=lambda x: -x[1]):
            status = "✓ saturated" if n >= 3 else ("~ approaching" if n >= 2 else "✗ needs more")
            lines.append(f"| {cat} | {n} | {status} |")
    lines.append("")

    # Memos
    if memos:
        lines.append("## Memos\n")
        for m in memos:
            if not isinstance(m, dict):
                continue
            text = m.get("text", "")
            codes = m.get("codes", [])
            prefix = f"[{', '.join(codes)}] " if codes else ""
            lines.append(f"- {prefix}{text}")
        lines.append("")

    # EARS Pattern Mapping
    if codebook:
        lines.append("## EARS Requirements Mapping\n")
        lines.append(
            "Use these EARS patterns (Mavin et al. 2009) when converting "
            "failure codes to Kiro spec requirements:\n"
        )
        lines.append("| Failure Code | EARS Pattern | Requirement Template |")
        lines.append("|-------------|--------------|---------------------|")
        for code in codebook[:7]:
            if not isinstance(code, dict):
                continue
            name = code.get("name", "")
            lines.append(
                f"| {name} | Unwanted Behaviour | "
                f"IF {_cell(name.lower(), 40)} is detected, "
                f"THEN the agent SHALL ... |"
            )
        lines.append("")
        lines.append(
            "> **EARS patterns:** Ubiquitous (always active), "
            "Event-driven (WHEN trigger), State-driven (WHILE condition), "
            "Unwanted Behaviour (IF fault THEN response), "
            "Complex (WHILE + WHEN)\n"
        )

    # Judge Prompt
    judge = storage.get("_generated_judge_prompt") or storage.get("_simple_judge_prompt") or ""
    if judge.strip():
        lines.append("## Judge Prompt\n")
        lines.append(f"```\n{judge.strip()}\n```\n")

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _verdict(ann: dict) -> str:
    """Normalize verdict from various annotation shapes."""
    v = ann.get("annotation", "") or ""
    if not v:
        codes = ann.get("codes", [])
        if codes:
            return "incorrect"
    return v.lower().strip()


def _cell(text: str, limit: int = 80) -> str:
    """Escape and truncate text for markdown table cells."""
    t = text.replace("|", "\\|").replace("\n", " ")
    if len(t) > limit:
        return t[:limit - 1] + "…"
    return t


def _list_items(items: list) -> str:
    return "\n".join(f"- {item}" for item in items)


def _code_frequencies(annotations: list[dict]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for ann in annotations:
        codes = ann.get("codes", [])
        if isinstance(codes, str):
            codes = [codes]
        for code in codes:
            if code:
                freq[code] = freq.get(code, 0) + 1
    return freq


def _code_severity(code_name: str, annotations: list[dict]) -> str:
    """Return the most common severity for a given code."""
    sevs: dict[str, int] = {}
    for ann in annotations:
        codes = ann.get("codes", [])
        if isinstance(codes, str):
            codes = [codes]
        if code_name in codes:
            s = ann.get("severity", "functional")
            sevs[s] = sevs.get(s, 0) + 1
    if not sevs:
        return "functional"
    return max(sevs, key=lambda k: sevs[k])
