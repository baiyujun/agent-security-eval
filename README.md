# Agent Security Eval

Infrastructure for executable security evaluation and feedback-guided fuzzing of tool-using AI
agents.

The system is intended to generate and mutate attack scenarios, execute them in isolated target
environments, observe real tool calls, guardrail events, and environmental side effects, and
produce reproducible `RunOutcome` artifacts from explicit security assertions.

## Status

This repository is at the initial project-skeleton stage. The architecture documents describe the
intended boundaries; external framework integrations and security evaluation features are not yet
implemented.

## Core principles

- The Campaign Controller is the only top-level controller.
- Inspect AI is planned as the Batch / Sample execution backend.
- promptfoo is only a candidate-generation backend.
- PyRIT is only an Attack Policy within an individual Run.
- The Final Assertion Engine is the sole formal source of security truth.
- Attack generation and security adjudication remain separate.
- Security and normal-task utility are evaluated separately.
- Black-box, gray-box, and controlled white-box results are reported separately.
- External frameworks connect through Adapters and do not become the project domain model.

## Non-goals

- This is not a malicious-prompt or intent text classifier.
- This is not a production online `allow` / `block` gateway.
- A single security score does not replace structured outcomes.
- Attack-generator labels and LLM-grader labels are not final truth.

## Repository structure

```text
.github/workflows/       Continuous integration
docs/architecture/       Architecture baseline
docs/adr/                Architecture decisions
docs/development/        Delivery roadmap
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
pytest
```

## Legacy project

The historical layered intent-recognition and online guardrail prototype is preserved at
<https://github.com/baiyujun/intent-engine-legacy>.

## License status

Repository license and ownership terms are pending confirmation.
Do not copy third-party code or datasets without recording their exact
source, version, license, and permitted use.
