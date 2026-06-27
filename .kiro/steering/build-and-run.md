---
inclusion: always
---

# GEDD Build, Run & Quality Commands

## Setup
```bash
cd grounded-evals
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the App
```bash
grounded-evals serve --host 127.0.0.1 --port 8080
```
Opens at http://127.0.0.1:8080. Guest mode by default.

## LLM Provider
Option A (Bedrock — default):
```bash
export AWS_REGION=us-east-1
```

Option B (Direct Anthropic):
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Tests
```bash
cd grounded-evals
python -m pytest tests/ -q --tb=short
```

## Linting
```bash
ruff check src/ tests/
ruff check src/ --fix          # auto-fix
ruff format src/ tests/        # format
```

## Type Checking
```bash
mypy src/ --strict
```

## Docker
```bash
cd grounded-evals
docker build -t grounded-evals .
docker run -e AWS_REGION=us-east-1 -p 8080:8080 grounded-evals
```

## CDK Deploy
```bash
cd grounded-evals/infra
pip install -r requirements.txt
cdk synth --no-lookups    # validate
cdk deploy --all          # deploy
```

## CI Pipeline (GitHub Actions)
On push/PR to main:
1. pytest suite
2. ruff lint + format check
3. Trivy security scan (HIGH/CRITICAL)
4. TruffleHog secret detection
5. CDK synthesis validation
