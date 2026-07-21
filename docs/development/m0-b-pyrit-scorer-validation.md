# M0-B Assertion-Backed PyRIT Scorer Validation

## Verdict

**PASS for the review-corrected bounded M0-B scorer-boundary validation.** On 2026-07-17, the
corrected local gates and Draft PR #7 GitHub Actions passed. The project-owned Progress Oracle
contract maps into the pinned PyRIT `0.14.0` true/false scorer interface without losing Run
identity, terminal state, invalid-Run state, attack stage, progress features, evidence IDs, or
project metadata.

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
- a required `AttackStage`: `NONE`, `DELIVERED`, `INFLUENCED`, `ATTEMPTED`, `EXECUTED`, or `EFFECT`;
- JSON-compatible `progress_features`;
- `internal_rationale` for trusted audit and `policy_feedback` for attacker-visible feedback;
- evidence IDs; and
- JSON-compatible project metadata.

`OBJECTIVE_ACHIEVED` requires at least one evidence ID. This prevents an Agent's response text from
becoming sufficient evidence for an observed environmental effect. The asynchronous
`ProgressOracle` protocol receives the scorer-bound Run ID and candidate response and returns the
project decision.

`internal_rationale` may contain private evidence detail and remains inside the complete decision
JSON. Only Oracle-sanitized `policy_feedback` becomes PyRIT `Score.score_rationale`. PyRIT attack
implementations may append `score_rationale` to the adversarial model when
`use_score_as_feedback=True`, so project code must never substitute internal rationale there. Full
score metadata remains a trusted project recovery surface and must not be forwarded to the attacker.

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
`ProgressDecision.model_dump_json()` value under `progress_decision` for lossless recovery. The flat
fields also include `stage_reached` for policy control without parsing the full internal payload.

If an Oracle returns a decision for a different Run, the adapter emits a new `INVALID_RUN` decision
for the bound Run. It records the reported Run ID for diagnosis and discards all foreign evidence.

## Public Blocked and Error Path

PyRIT `0.14.0` normally filters error-typed blocked/error pieces before calling a piece-level
`TrueFalseScorer`, then emits a metadata-free fallback `False`. The project adapter overrides
PyRIT's message-level `_score_async()` subclass extension point so inherited public `score_async()`
calls the Oracle for every validated single-piece message. The automated proof covers normal text,
blocked empty content, blocked partial content, and other Target errors.

For a blocked piece, string `prompt_metadata["partial_content"]` is passed to the Oracle when
present; otherwise its converted value is used. An explicit caller request for
`skip_on_error_result=True` retains PyRIT's documented opt-out and returns no score before the
subclass extension point.

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
8. Error-typed blocked content reaches the Oracle through public `score_async()` and retains a
   complete `TERMINAL_BLOCKED` decision.
9. Blocked partial content reaches the Oracle instead of PyRIT's fallback.
10. Other Target errors retain a complete `INVALID_RUN` decision.
11. Canary-bearing internal rationale never becomes `score_rationale`; sanitized policy feedback
    does.

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
  src/agentsec_eval/assertions/__init__.py \
  src/agentsec_eval/assertions/progress.py \
  src/agentsec_eval/integrations/pyrit/__init__.py \
  src/agentsec_eval/integrations/pyrit/scorer.py \
  tests/unit/assertions/test_progress.py \
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
- core non-Docker Pytest: `39 passed, 2 deselected`;
- explicit corrected-boundary MyPy: `Success: no issues found in 7 source files`;
- focused M0-B Pytest: `15 passed`; and
- unchanged M0-A Docker Pytest: `2 passed in 59.33s`.

Draft PR #7 review-corrected Head results:

- `quality`: passed in 44 seconds;
- `m0a-docker`: passed in 1 minute 36 seconds; and
- `m0b-pyrit`: passed in 1 minute 54 seconds.

## Known Limitations

- M0-B validates PyRIT `0.14.0` only; version changes require contract retesting.
- It does not instantiate or run an Attack Strategy or PromptTarget.
- It exposes terminal metadata but does not own turn limits, budget exhaustion, or loop stopping.
- It proves deterministic Mock Receiver evidence handling, not a complete Final Assertion Engine.
- The Oracle owns `policy_feedback` sanitization. M0-B proves that the adapter never substitutes
  internal rationale; it does not implement a general secret detector.
- Complete decision JSON is trusted internal metadata, not policy feedback. M0-C must preserve that
  boundary when it consumes terminal and stage fields.
- It does not claim process-global `CentralMemory` isolation, cancellation safety, persistence, or
  multi-process behavior.
- No `BaseScenario`, `ScenarioCase`, AttackSeed, Scenario Registry, external Benchmark Runtime
  Adapter, importer, or dataset is introduced.
- `m0a_harness.py` remains unchanged bounded validation code and is not promoted into a production
  execution backend.
