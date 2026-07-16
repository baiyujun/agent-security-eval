# Agent Security Eval

Infrastructure for executable security evaluation and feedback-guided fuzzing of tool-using AI
agents.

The system is intended to generate and mutate attack scenarios, execute them in isolated target
environments, observe real tool calls, guardrail events, and environmental side effects, and
produce reproducible evaluation artifacts from explicit security assertions.

## Status

This repository is at an early execution-validation stage. M0-A now provides a minimal formal
Inspect AI `0.3.246` boundary and automated Docker evidence; it is not a complete security
evaluation system or production execution backend. The current evidence and decisions are recorded
in:

- [reference reuse analysis](docs/reference-reuse-analysis.md);
- [candidate architecture options](docs/architecture/reference-informed-options.md); and
- [M0-A Inspect execution validation](docs/development/m0-a-inspect-validation.md); and
- [the throwaway Inspect AI execution spike](experiments/inspect-execution-model/README.md).

The throwaway spike remains research evidence only. M0-A independently implements project-owned
domain and Target boundaries under `src/agentsec_eval/`; it does not freeze a complete product
layout or persistent model.

## Core principles

- The Campaign Controller is the only top-level controller.
- Inspect AI is validated by M0-A as the Batch / Sample execution candidate; the production backend
  remains incomplete.
- promptfoo is only a candidate-generation backend.
- PyRIT is only an Attack Policy within an individual Run.
- The Final Assertion Engine is the sole formal source of security truth.
- Attack generation and security adjudication remain separate.
- Security and normal-task utility are evaluated separately.
- Black-box, gray-box, and controlled white-box results are reported separately.
- Third-party runtime types remain inside integration/import boundaries unless later evidence
  justifies a durable project contract.

## Non-goals

- This is not a malicious-prompt or intent text classifier.
- This is not a production online `allow` / `block` gateway.
- A single security score does not replace structured outcomes.
- Attack-generator labels and LLM-grader labels are not final truth.

## Current research layout

This is the present repository layout, not a proposed final product architecture.

```text
.github/workflows/       Continuous integration
docs/architecture/       Architecture baseline
docs/adr/                Architecture decisions
docs/development/        Delivery roadmap
experiments/             Throwaway architecture-risk experiments
references/              Versioned third-party reference registry
src/agentsec_eval/       Python package
tests/                   Automated tests
```

## Local development

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

ruff check .
ruff format --check .
mypy
pytest -m "not docker"
```

The M0-A integration tests also require a working Docker daemon and Docker Compose. They use a
deterministic Fake Target, an internal Compose network, and Inspect's no-key mock model:

```bash
docker version
docker compose version
pytest -m docker tests/integration/m0a
```

## Legacy project

The historical layered intent-recognition and online guardrail prototype is preserved at
<https://github.com/baiyujun/intent-engine-legacy>.

## License status

No formal open-source license has been selected, and this repository currently grants no license
for reuse beyond rights provided by applicable law. Ownership terms are pending confirmation.
Do not copy third-party code or datasets without recording their exact
source, version, license, and permitted use.
