# TDD Evidence: M0-B Assertion-Backed PyRIT Scorer Validation

## Cycle 1: Durable Execution Inputs

### Target Behavior

Durable M0-A models reject unknown fields and whitespace-only primary IDs while preserving valid
serialization and immutability.

### RED

- **Tests added**: unknown-field and blank-ID cases in `tests/unit/domain/test_models.py`.
- **Command**: `pytest tests/unit/domain/test_models.py -q`.
- **Observed failure**: `5 failed`; extra fields and whitespace-only IDs were accepted.
- **Failure is correct because**: frozen Pydantic models did not yet forbid extras or constrain
  durable identifiers.

### GREEN

- **Minimal implementation**: configured the shared frozen model with `extra="forbid"` and applied a
  stripped, non-empty string annotation only to `run_id`, `target_id`, `scenario_id`, and
  `candidate_id`.
- **Command**: `pytest tests/unit/domain/test_models.py -q`.
- **Observed pass**: `15 passed`.

### REFACTOR

- **Refactor done**: no.
- **Reason**: the shared model configuration and one private ID annotation were the minimal change.

## Cycle 2: Progress Oracle Contract

### Target Behavior

Project code owns four unambiguous progress states, requires evidence for objective achievement,
round-trips complete decision state, and imports no PyRIT package.

### RED

- **Tests added**: `tests/unit/assertions/test_progress.py` and
  `tests/unit/assertions/test_assertions_pyrit_boundary.py`.
- **Command**: `pytest tests/unit/assertions -q`.
- **Observed failure**: collection stopped with
  `ModuleNotFoundError: No module named 'agentsec_eval.assertions'`.
- **Failure is correct because**: the project assertion boundary did not exist.

### GREEN

- **Minimal implementation**: added `ProgressState`, immutable `ProgressDecision`, derived control
  properties, the achieved-objective evidence invariant, and the asynchronous `ProgressOracle`
  protocol.
- **Command**: `pytest tests/unit/assertions -q`.
- **Observed pass**: `8 passed`.

### REFACTOR

- **Refactor done**: no.
- **Reason**: the package is PyRIT-independent and exposes only the required runtime contract.

## Cycle 3: PyRIT True/False Adapter

### Target Behavior

A Run-bound project scorer satisfies PyRIT's real `TrueFalseScorer` contract, maps all four project
states exactly, and preserves the complete normalized decision in versioned score metadata.

### RED

- **Tests added**: `tests/unit/integrations/pyrit/test_scorer.py`.
- **Command**: `pytest tests/unit/integrations/pyrit -q`.
- **Observed failure**: collection stopped with
  `ModuleNotFoundError: No module named 'agentsec_eval.integrations'`.
- **Failure is correct because**: no PyRIT adapter package existed.

### GREEN

- **Minimal implementation**: added the exact optional `pyrit==0.14.0` dependency and a text-only,
  one-piece `AssertionBackedPyRITScorer` that binds one Run ID, invokes the Oracle, normalizes
  cross-Run decisions, and returns one real PyRIT `Score`.
- **Initial candidate result**: `5 failed, 2 passed` because PyRIT's metadata model converted Python
  booleans to integers.
- **Correction**: represented flat `terminal` and `invalid_run` controls as lowercase `"true"` and
  `"false"` strings, matching PyRIT's declared scalar metadata contract without mutating a validated
  `Score`.
- **Command**: `pytest tests/unit/integrations/pyrit -q`.
- **Observed pass**: `7 passed`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: kept the full typed project decision as JSON and limited flat fields to stable scalar
  controls, avoiding a second lossy project-state shape.

## Compatibility Evidence: Receiver and Concurrent Run Binding

The deterministic Mock Receiver integration tests passed on their first run after the unit-driven
adapter implementation. They are compatibility evidence, not a separate claimed RED/GREEN cycle.

- **Agent claim case**: text claiming Canary leakage without Receiver evidence returns `False` and
  `CONTINUE`.
- **Environment evidence case**: a matching bound-Run receipt returns `True`,
  `OBJECTIVE_ACHIEVED`, and its evidence ID.
- **Concurrency case**: two concurrently scored responses retain distinct Run and evidence IDs.
- **Boundary case**: only `agentsec_eval.integrations.pyrit` imports PyRIT in production source.
- **Focused command**: `pytest tests/unit/integrations/pyrit tests/integration/m0b
  tests/unit/integrations/test_pyrit_import_boundary.py`.
- **Observed pass before final delivery validation**: `11 passed`.
- **Focused type command**: explicit MyPy invocation over the two adapter files and two PyRIT test
  files.
- **Observed type result before final delivery validation**: `Success: no issues found in 4 source
  files`.

The final delivery run also recorded `38 passed, 2 deselected` for the core non-Docker suite and
`2 passed in 58.73s` for the unchanged M0-A Docker suite.

## Refactor Decision

No Attack Strategy, PromptTarget, loop control, scenario asset, Benchmark Adapter, dataset, or Final
Assertion Engine was added. Those concerns would obscure the one boundary under validation and are
deferred to their owning milestones.
