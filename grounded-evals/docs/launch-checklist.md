# GEDD Launch Checklist

Use this checklist before a public beta, workshop launch, or production launch of GEDD.

The current product is suitable for a controlled preview when the local test suite, route smoke test, docs, skill, plugin, and handoff paths pass. Treat it as production-ready only after the full browser workflow, auth modes, AWS deployment, and MLflow handoff have been verified in the target environment.

---

## Launch Decision

| Launch type | Minimum bar | Use when |
|-------------|-------------|----------|
| Internal preview | Local install, unit tests, route smoke, demo loading, README/setup accuracy | Team review, design critique, early PM feedback |
| Public beta | Internal preview checks plus browser E2E, fresh-user install, skill/plugin validation, security scan, known limits documented | Workshops, open-source announcement, early adopters |
| Production launch | Public beta checks plus Cognito auth, ECS deployment, TLS, persistent storage, MLflow handoff, monitoring, rollback, and support owner | External users depend on it for live evaluation work |

**Current recommendation:** launch as beta/preview until the browser E2E, deployed auth, AWS deployment, and MLflow handoff checks are complete.

---

## Release Evidence Header

Fill this out for every launch candidate.

| Field | Value |
|-------|-------|
| Release owner | |
| Target launch type | Internal preview / Public beta / Production |
| Git commit | |
| Git tag | |
| Environment | Local / Workshop / AWS ECS / Other |
| Python version | |
| AWS account/region | |
| Launch URL | |
| Rollback target | |
| Sign-off date | |

---

## 1. Repository And Release Hygiene

| Check | Command or evidence | Required for |
|-------|---------------------|--------------|
| Working tree is clean | `git status --short` has no output | All launches |
| Release commit is pushed | `git log -1 --oneline` and remote branch match | All launches |
| Version decision recorded | Tag, GitHub release, or documented beta label | Public beta, production |
| License and security docs present | `LICENSE`, `CONTRIBUTING.md`, `.github/SECURITY.md` | Public beta, production |
| No stale launch-blocking docs | Search for old workflow names and dead commands | Public beta, production |

Suggested stale-doc scan:

```bash
rg -n 'python -m grounded_evals\.app|Eight industries|5-step workflow|Step 3: Deploy|Claude Code conversation|\.codex/skills' \
  README.md SETUP.md grounded-evals/docs .agents plugins
```

---

## 2. Fresh Install

Run this from a clean virtual environment, not from a long-lived dev shell.

```bash
cd grounded-evals
python -m venv .venv-launch
source .venv-launch/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
grounded-evals --help
grounded-evals serve --help
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| Package installs | No resolver or build errors |
| Console script works | `grounded-evals --help` lists all commands |
| Serve command works | `grounded-evals serve --help` exits 0 |

---

## 3. Automated Test Gate

```bash
cd grounded-evals
PYTHONPATH=src pytest
PYTHONPATH=src python3 -m grounded_evals.cli --help
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| Unit and integration tests | All tests pass |
| CLI import path | Help command exits 0 |
| Diff hygiene | `git diff --check` exits 0 |

Run CDK synthesis before any AWS-backed launch:

```bash
cd grounded-evals
pip install -e ".[dev,deploy]"
cd infra
pip install -r requirements.txt
cdk synth --no-lookups
```

---

## 4. Website Smoke Test

Start the app locally:

```bash
cd grounded-evals
grounded-evals serve --host 127.0.0.1 --port 8080
```

In another shell:

```bash
for p in / /demos /coach /eval /coding /analysis /judge /report /health; do
  curl --http1.1 --max-time 10 -sS -o /tmp/gedd_page.out \
    -w "$p %{http_code} %{size_download}\n" \
    "http://127.0.0.1:8080$p"
done
```

Pass criteria:

| Route | Required result |
|-------|-----------------|
| `/health` | HTTP 200 and JSON status payload |
| All UI routes | HTTP 200 and non-empty response body |
| Server shutdown | Ctrl-C exits cleanly without leaving a port listener |

Route smoke testing is not a substitute for browser E2E. It only proves route registration and server rendering.

---

## 5. Browser E2E Gate

Complete this manually or with Playwright before public beta and production.

| Flow | Required result |
|------|-----------------|
| Homepage loads | User lands on Home in guest mode |
| Demos page loads | All 17 demo cards render without console errors |
| Load demo | Pick RxBot, TaxBot, or MigrateBot and confirm data appears across Coach, Eval Harness, Tag, Root Causes, Build Judge, and Report |
| New session | Start a blank agent and define name, domain, system prompt, and at least 3 golden queries |
| Eval Harness | Run or simulate responses without hanging the UI |
| Tag | Mark correct, partial, and incorrect responses; create a domain-specific error code and memo |
| Root Causes | Add or verify causal conditions, context, intervening conditions, strategies, and consequences |
| Build Judge | Generate or inspect rubric dimensions, hard-fail rules, and calibration summary |
| Report | Export JSON/session artifacts and verify the file imports back into a fresh browser session |
| Responsive layout | Repeat core navigation at desktop and mobile widths |

Launch-blocking browser issues:

| Issue | Why it blocks |
|-------|---------------|
| Demo load loses required session data | Users cannot inspect the main proof path |
| Export/import corrupts `session.json` | Handoff contract is unreliable |
| Tag or judge pages cannot save work | Core GEDD workflow is broken |
| Text overlaps controls on common viewports | Workshop users cannot complete the flow |
| Console errors on route load | Hidden UI failures may break live sessions |

---

## 6. Domain Expert Workflow Gate

Run one end-to-end expert scenario using a high-risk demo.

Recommended demos:

| Demo | Why |
|------|-----|
| RxBot | Tests catastrophic safety language such as dosage unit confusion |
| TaxBot | Tests liability boundaries and CPA escalation |
| MigrateBot | Tests legal threshold reasoning and statutory bars |
| InsureBot | Tests coverage hallucination and bad-faith risk |

Pass criteria:

| Artifact | Required result |
|----------|-----------------|
| Golden queries | At least 15 for a production handoff, or explicit beta note if thinner |
| Error codebook | Uses domain vocabulary, not generic labels only |
| Memos | Explain user harm, not just model behavior |
| Paradigm model | Includes causal conditions and consequences |
| Judge | Contains rubric dimensions and hard-fail rules tied to observed failures |
| Export | Produces a reusable `session.json` or handoff JSON |

---

## 7. CLI And Handoff Gate

Use a representative session file from the website or a curated fixture.

```bash
cd grounded-evals
grounded-evals validate-session --session session.json
grounded-evals handoff --session session.json --output launch_handoff_session.json
grounded-evals export --session session.json --format jsonl --output launch_golden.jsonl
grounded-evals judge --session session.json --output launch_judge.md
grounded-evals status --session session.json
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| Validation | No blocking errors |
| Handoff JSON | Includes schema version, agent spec, prompts, annotations, and validation metadata |
| Golden JSONL | One valid JSON object per query |
| Judge prompt | Contains criteria derived from observed error codes |
| Status | Correctly summarizes agent, query count, annotation count, and readiness |

---

## 8. Codex Skill And Plugin Gate

Validate both the repo-scoped skill and installable plugin package.

| Asset | Required result |
|-------|-----------------|
| `.agents/skills/gedd/SKILL.md` | Valid skill metadata and website-first instructions |
| `plugins/gedd/.codex-plugin/plugin.json` | Valid manifest with `skills: "./skills/"` |
| `plugins/gedd/skills/gedd/SKILL.md` | Same launch-safe workflow as repo skill |
| `.agents/plugins/marketplace.json` | Local marketplace points to `./plugins/gedd` |

Codex validator paths are installation-specific. In Codex, use `$skill-creator` and `$plugin-creator` validators, or run the local validator scripts for your machine and record the exact output in release evidence.

Manual prompt checks:

```text
Use $gedd to evaluate my AI agent with the website-first workflow.
Use $gedd to package my current session for ML engineering handoff.
Use $gedd to build a judge from the domain expert's failure codes.
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| Skill trigger | Codex selects or accepts `$gedd` for GEDD work |
| First recommendation | Starts with the website unless user asks for CLI-only automation |
| Handoff guidance | Includes `validate-session`, `handoff`, `export`, `judge`, and `mlflow` where relevant |
| Plugin install | Plugin appears through repo marketplace after Codex restart |

---

## 9. Auth And Session Gate

Verify each auth mode you plan to support at launch.

| Mode | Setup | Required result |
|------|-------|-----------------|
| Guest mode | No `ADMIN_PASSWORD`, no Cognito env vars | `/` loads without login |
| Password mode | `ADMIN_PASSWORD` set | Protected routes redirect to `/login`; correct password succeeds; wrong password fails |
| Cognito mode | `COGNITO_USER_POOL_ID` and `COGNITO_CLIENT_ID` set | Valid user signs in; invalid user fails; logout/session expiry behavior is understood |

Session persistence checks:

| Check | Required result |
|-------|-----------------|
| Local restart | Users understand that auto-generated `STORAGE_SECRET` changes browser session validity after restart |
| Deployed ECS | `STORAGE_SECRET` comes from Secrets Manager |
| Export-first guidance | Docs warn users to export before closing browser or loading demos |
| EFS deployment | `NICEGUI_STORAGE_PATH` is mounted and writable in ECS |

---

## 10. AWS Deployment Gate

Required for production launch.

Infrastructure:

```bash
cd grounded-evals
./scripts/deploy-infra.sh --cert arn:aws:acm:REGION:ACCOUNT:certificate/CERT_ID
```

Container:

```bash
cd grounded-evals
./scripts/deploy-ui.sh
```

Optional AgentCore runtime:

```bash
cd grounded-evals
./scripts/deploy-agent.sh
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| CDK deploy | Completes without manual drift or failed stacks |
| TLS | Public launch URL uses HTTPS |
| ECS health | Service reaches steady state |
| ALB health | Target group reports healthy tasks |
| Cognito | Auth callback works against launch URL |
| Secrets | `STORAGE_SECRET` and password fallback are stored in Secrets Manager |
| Bedrock IAM | ECS task role can invoke required models |
| Logs | CloudWatch logs capture app startup and route errors |
| Rollback | Previous image or commit can be redeployed within the agreed window |

Useful AWS checks:

```bash
aws cloudformation describe-stacks --region "$AWS_REGION"
aws ecs describe-services --region "$AWS_REGION" --cluster CLUSTER --services SERVICE
aws elbv2 describe-target-health --region "$AWS_REGION" --target-group-arn TARGET_GROUP_ARN
aws logs tail /aws/ecs/gedd --since 30m --region "$AWS_REGION"
```

---

## 11. MLflow And CI Gate

Required before promising production evaluation automation.

```bash
cd grounded-evals
pip install sagemaker-mlflow "mlflow>=3.0"

grounded-evals mlflow \
  --session launch_handoff_session.json \
  --tracking-uri arn:aws:sagemaker:REGION:ACCOUNT:mlflow-tracking-server/SERVER \
  --run-eval
```

Pass criteria:

| Check | Required result |
|-------|-----------------|
| MLflow connection | Tracking server accepts the run |
| Dataset | Golden queries appear as an eval dataset |
| Judges | Error-code-derived custom judges are created |
| Artifacts | Session, judge prompt, and dataset are logged |
| CI gate | A workflow can run `grounded-evals mlflow --run-eval` using the launch session |
| Regression threshold | Team agrees on TSR, kappa, and hard-fail thresholds |

---

## 12. Security, Privacy, And Compliance Gate

| Check | Required result |
|-------|-----------------|
| Secret scan | No verified secrets in repo history or release diff |
| Dependency scan | No unresolved critical/high vulnerabilities accepted without owner sign-off |
| Demo data review | Demo scenarios contain no real customer, patient, student, policyholder, or employee data |
| Auth posture | Guest mode disabled for production deployments unless explicitly intentional |
| Data retention | Session storage behavior is documented for workshop and production users |
| Logs | Logs do not contain API keys, passwords, or full sensitive user submissions by default |
| Model access | Bedrock and Anthropic use approved accounts, regions, and models |
| Security contact | `.github/SECURITY.md` is accurate |

---

## 13. Documentation Gate

| Audience | Required doc path | Required result |
|----------|-------------------|-----------------|
| First-time user | `README.md` | Website is the first option; demos and domain expert discovery are clear |
| Engineer | `SETUP.md` | Local setup, providers, auth, env vars, and deployment are current |
| Domain expert | `grounded-evals/docs/domain-expert-guide.md` | No CLI required to understand the workflow |
| ML engineer | `grounded-evals/docs/pipeline-guide.md` | Handoff and MLflow path are executable |
| Codex user | `README.md`, `.agents/skills/gedd/SKILL.md`, `plugins/gedd/skills/gedd/SKILL.md` | Skill vs plugin expectations are clear |
| Maintainer | This checklist | Launch gates are repeatable |

---

## 14. Launch Day Runbook

| Phase | Action | Owner |
|-------|--------|-------|
| T-24h | Freeze launch commit and run automated tests | |
| T-24h | Run browser E2E and export/import proof | |
| T-12h | Deploy to target environment and verify health | |
| T-4h | Run MLflow handoff proof if production claims include CI gates | |
| T-2h | Confirm rollback command and owner availability | |
| Launch | Publish README/release/demo link | |
| Launch + 1h | Monitor app logs, support channel, and GitHub issues | |
| Launch + 24h | Review failures, docs confusion, and first-user friction | |

Rollback checklist:

```bash
git rev-parse HEAD
git log --oneline -5
# Rebuild and redeploy the previous known-good image or revert to the previous release tag.
```

No-go conditions:

| Condition | Action |
|-----------|--------|
| Tests fail on release commit | Do not launch |
| Website cannot load demos | Do not launch public beta |
| Export/import fails | Do not launch public beta or production |
| Auth fails in target deployment | Do not launch production |
| ECS target group unhealthy | Do not launch production |
| MLflow run fails | Remove MLflow/CI claims or block production launch |
| Verified secret in repo or image | Rotate secret and block launch |

---

## 15. Post-Launch Review

Run this review after the first workshop, beta announcement, or production week.

| Question | Evidence |
|----------|----------|
| Could a new user start from the website without help? | |
| Which page caused the most confusion? | |
| Did users export usable handoff artifacts? | |
| Did experts create domain-specific error codes? | |
| Did ML engineers successfully run `validate-session`, `judge`, and `mlflow`? | |
| Were any failures missing from the launch checklist? | |
| What should block the next launch that did not block this one? | |
