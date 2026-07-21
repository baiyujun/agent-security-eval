# Agent Security Eval

Infrastructure for executable security evaluation and feedback-guided fuzzing of tool-using AI
agents.

The system is intended to generate and mutate attack scenarios, execute them in isolated target
environments, observe real tool calls, guardrail events, and environmental side effects, and
produce reproducible evaluation artifacts from explicit security assertions.

## Status

The bounded M0 validation phase is complete:

- **M0-A:** Inspect AI execution boundary;
- **M0-B:** assertion-backed progress scorer; and
- **M0-C:** per-Run adaptive PyRIT policy.

M0 proves that a project-owned Run can cross a pinned Inspect AI `0.3.246` execution boundary,
produce project-native Target and trace evidence, map a project Progress Oracle into PyRIT `0.14.0`,
and run a bounded adaptive policy with project-owned stopping semantics. Inspect owns isolated
Batch/Sample execution inside the integration boundary. PyRIT owns adaptive prompt selection and
progress feedback inside one Run. The project continues to own Run identity, Target Sessions,
Canonical Trace, Oracle decisions, terminal states, and final security truth.

M0 is not a complete product. It does not provide a production execution backend, Campaign
Controller, Final Assertion Engine, scenario registry, benchmark importer, dataset, persistence,
distributed workers, or a parallel PyRIT policy backend. See the
[M0 closeout report](docs/development/m0-closeout.md) and the individual
[M0-A](docs/development/m0-a-inspect-validation.md),
[M0-B](docs/development/m0-b-pyrit-scorer-validation.md), and
[M0-C](docs/development/m0-c-pyrit-policy-validation.md) validation reports.

## Core principles

- The Campaign Controller is the only top-level controller.
- Inspect AI is the validated Batch/Sample execution boundary; the M0-A Harness is not a production
  backend.
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
pytest -m "not docker" \
  --ignore=tests/unit/integrations/pyrit \
  --ignore=tests/integration/m0b \
  --ignore=tests/integration/m0c
```

The optional PyRIT integration has a separate pinned dependency and test boundary:

```bash
pip install -e ".[dev,pyrit]"
python -c 'from importlib.metadata import version; assert version("pyrit") == "0.14.0"'
pytest \
  tests/unit/integrations/pyrit \
  tests/integration/m0b \
  tests/integration/m0c \
  tests/unit/integrations/test_pyrit_import_boundary.py
```

The M0-A integration tests require a working Docker daemon and Docker Compose. They use a
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
