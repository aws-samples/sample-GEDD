## What

<!-- Brief description of the change -->

## Why

<!-- Link to issue or explain motivation -->

## Findings impact

<!-- Does this change a number in FINDINGS.md or README.md? If so, re-run the script that produces it,
commit the regenerated results, and update the finding's status and date. -->

- [ ] No finding changes
- [ ] Findings updated: <!-- F-ids, e.g. F1, F3 -->

## Checklist

- [ ] Tests pass locally (`cd grounded-evals && pytest tests/`)
- [ ] Findings reproduce (`cd experiments/docile-invoices && uv run python 08_rigor.py && uv run python 09_reward_gate_ppi.py && uv run python 12_reward_audit.py`, no diff in `results/`)
- [ ] No new secrets or credentials in code
- [ ] IAM policies use least-privilege (resource-scoped, no `*`)
- [ ] CDK synth succeeds (`cd infra && cdk synth`)
- [ ] No `TODO` or `FIXME` left unresolved
