# M0-B Assertion-Backed PyRIT Scorer Validation

## Verdict

**PASS for the bounded M0-B scorer-boundary validation.** On 2026-07-17, the local gates and Draft
PR #7 GitHub Actions passed. The project-owned Progress Oracle contract maps into the pinned PyRIT
`0.14.0` true/false scorer interface without losing Run identity, terminal state, invalid-Run state,
rationale, evidence IDs, or project metadata.

This verdict does not mean an Attack Strategy, Attack Policy stopping loop, PromptTarget, Campaign
Controller, Final Assertion Engine, scenario asset model, M0-C, or M1 is complete.

## Purpose and Boundary

M0-B validates one narrow path:

```text
ProgressOracle
    -> ProgressDecision
    -> AssertionBackedPyRITScorer
    -> PyRIT true_false Score + complete project metadata
```

`agentsec_eval.assertions` owns project truth and has no PyRIT dependency. Only
`agentsec_eval.integrations.pyrit` imports PyRIT. The adapter binds one explicit Run ID at
construction and passes that ID to the Oracle; candidate response text cannot select the Run.

The dependency remains optional and pinned exactly:

```toml
pyrit = [
  "pyrit==0.14.0",
]
```

Core quality and M0-A Docker jobs continue to install `.[dev]`. A dedicated `m0b-pyrit` job installs
`.[dev,pyrit]` and runs the optional integration's type and behavior checks.

## Project Progress Contract

`ProgressDecision` is an immutable, extra-forbidden project model containing:

- a non-empty `run_id`;
- one of `CONTINUE`, `OBJECTIVE_ACHIEVED`, `TERMINAL_BLOCKED`, or `INVALID_RUN`;
- a rationale;
- evidence IDs; and
- JSON-compatible project metadata.

`OBJECTIVE_ACHIEVED` requires at least one evidence ID. This prevents an Agent's response text from
becoming sufficient evidence for an observed environmental effect. The asynchronous
`ProgressOracle` protocol receives the scorer-bound Run ID and candidate response and returns the
project decision.

As a small prerequisite hardening, durable M0-A models now forbid unknown fields and reject blank
`run_id`, `target_id`, `scenario_id`, and `candidate_id` values. Their existing serialized names and
valid behavior are unchanged.

## PyRIT Mapping

| Project state | PyRIT value | `terminal` | `stop_reason` | `invalid_run` |
|---|---:|---|---|---|
| `CONTINUE` | `False` | `"false"` | empty | `"false"` |
| `OBJECTIVE_ACHIEVED` | `True` | `"true"` | `objective_achieved` | `"false"` |
| `TERMINAL_BLOCKED` | `False` | `"true"` | `blocked` | `"false"` |
| `INVALID_RUN` | `False` | `"true"` | `invalid_run` | `"true"` |

Only `OBJECTIVE_ACHIEVED` maps to `True`. Treating `TERMINAL_BLOCKED` as true would incorrectly tell
PyRIT that the attack succeeded. M0-B preserves the terminal signal but deliberately does not stop
an attack loop; M0-C will interpret the metadata at the policy boundary.

PyRIT `0.14.0` declares score metadata as scalar `str | int | float` values and normalizes Python
booleans to integers. The adapter therefore uses unambiguous lowercase string flags for `terminal`
and `invalid_run`. Metadata schema version `1` stores flat control fields plus the complete
`ProgressDecision.model_dump_json()` value under `progress_decision` for lossless recovery.

If an Oracle returns a decision for a different Run, the adapter emits a new `INVALID_RUN` decision
for the bound Run. It records the reported Run ID for diagnosis and discards all foreign evidence.

## Automated Evidence

The focused compatibility tests use real PyRIT `MessagePiece`, `Score`, `TrueFalseScorer`, and
`AttackScoringConfig` types. They prove:

1. PyRIT accepts `AssertionBackedPyRITScorer` as an objective scorer.
2. Each scorer instance uses its constructor-bound Run ID.
3. An Agent text claim without Receiver evidence maps to `False` and `CONTINUE`.
4. matching Receiver evidence for the bound Run maps to `True` and `OBJECTIVE_ACHIEVED`.
5. `TERMINAL_BLOCKED` remains false while retaining its terminal and stop-reason fields.
6. `INVALID_RUN` remains distinguishable from continuation and objective achievement.
7. Concurrent scorer instances retain separate Run IDs and evidence IDs.

AST dependency tests also prove that `agentsec_eval.assertions` imports no PyRIT module and every
production PyRIT import remains under `agentsec_eval.integrations.pyrit`.

The integration proof initializes PyRIT's in-memory database because public `score_async()` writes
through `CentralMemory`. Concurrent results prove scorer-instance Run binding only. They do not
prove isolation of PyRIT's process-global `CentralMemory`.

## Reproduction

Install the optional integration on Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,pyrit]"
```

Run the core, optional integration, and existing Docker gates:

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker" \
  --ignore=tests/unit/integrations/pyrit \
  --ignore=tests/integration/m0b
mypy \
  src/agentsec_eval/integrations/pyrit/__init__.py \
  src/agentsec_eval/integrations/pyrit/scorer.py \
  tests/unit/integrations/pyrit/test_scorer.py \
  tests/integration/m0b/test_pyrit_scorer.py
pytest \
  tests/unit/integrations/pyrit \
  tests/integration/m0b \
  tests/unit/integrations/test_pyrit_import_boundary.py
pytest -m docker tests/integration/m0a
git diff --check
```

Observed local results on 2026-07-17 before delivery:

- Ruff check: passed;
- Ruff format check: `31 files already formatted`;
- core MyPy: `Success: no issues found in 26 source files`;
- core non-Docker Pytest: `38 passed, 2 deselected`;
- explicit PyRIT integration MyPy: `Success: no issues found in 4 source files`;
- focused M0-B Pytest: `11 passed`; and
- unchanged M0-A Docker Pytest: `2 passed in 58.73s`.

Draft PR #7 GitHub Actions results:

- `quality`: passed in 55 seconds;
- `m0a-docker`: passed in 1 minute 33 seconds; and
- `m0b-pyrit`: passed in 1 minute 50 seconds.

## Known Limitations

- M0-B validates PyRIT `0.14.0` only; version changes require contract retesting.
- It does not instantiate or run an Attack Strategy or PromptTarget.
- It exposes terminal metadata but does not own turn limits, budget exhaustion, or loop stopping.
- It proves deterministic Mock Receiver evidence handling, not a complete Final Assertion Engine.
- It does not claim process-global `CentralMemory` isolation, cancellation safety, persistence, or
  multi-process behavior.
- No `BaseScenario`, `ScenarioCase`, AttackSeed, Scenario Registry, Benchmark Adapter, importer, or
  dataset is introduced.
- `m0a_harness.py` remains unchanged bounded validation code and is not promoted into a production
  execution backend.
