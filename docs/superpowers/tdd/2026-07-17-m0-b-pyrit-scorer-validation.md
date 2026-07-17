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

## Cycle 4: Complete Progress Decision Contract

### Target Behavior

The unmerged metadata v1 contract carries a required attack stage, typed JSON progress features,
trusted internal rationale, and separately sanitized policy feedback.

### RED

- **Test added**: complete decision round-trip assertions in
  `tests/unit/assertions/test_progress.py`.
- **Command**: `pytest tests/unit/assertions/test_progress.py -q`.
- **Observed failure**: collection failed with `ImportError: cannot import name 'AttackStage'`.
- **Failure is correct because**: the project decision contract had no stage vocabulary or split
  feedback fields.

### GREEN

- **Minimal implementation**: added the six-value `AttackStage`, required `stage_reached`,
  `progress_features`, `internal_rationale`, and `policy_feedback`; exported the stage type from the
  PyRIT-independent assertions package.
- **Command**: `pytest tests/unit/assertions -q`.
- **Observed pass**: `8 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no compatibility alias for the draft-only `rationale` field was retained.

## Cycle 5: Trusted Rationale and Policy Feedback

### Target Behavior

Canary-bearing internal audit detail remains recoverable in the complete decision JSON, while only
Oracle-sanitized policy feedback becomes PyRIT `Score.score_rationale`.

### RED

- **Test added**:
  `test_scorer_exposes_only_sanitized_policy_feedback_as_rationale`.
- **Command**: `pytest tests/unit/integrations/pyrit/test_scorer.py -q`.
- **Observed failure**: `6 failed, 2 passed`; the adapter accessed removed
  `decision.rationale`, and cross-Run normalization lacked the required stage.
- **Failure is correct because**: one draft field still served both audit and attacker feedback.

### GREEN

- **Minimal implementation**: mapped only `policy_feedback` to `score_rationale`, kept
  `internal_rationale` in the complete decision JSON, added flat `stage_reached`, and made cross-Run
  normalization emit stage `NONE` plus sanitized generic feedback.
- **Command**: `pytest tests/unit/integrations/pyrit/test_scorer.py -q`.
- **Observed pass**: `8 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: the existing single Score builder remained the one translation point.

## Cycle 6: Public Blocked and Error Scoring

### Target Behavior

Inherited public `score_async()` calls the project Oracle and preserves complete decisions for
error-typed blocked empty content, blocked partial content, and other Target errors.

### RED

- **Tests added**: three public-path cases in `tests/integration/m0b/test_pyrit_scorer.py`.
- **Command**: `pytest tests/integration/m0b/test_pyrit_scorer.py -q`.
- **Observed failure**: `3 failed, 3 passed`; every new Oracle call list was empty because PyRIT
  emitted its metadata-free fallback score.
- **Failure is correct because**: the adapter only overrode piece-level scoring, which error-typed
  pieces never reached.

### GREEN

- **Minimal implementation**: overrode the message-level `_score_async()` extension point to route
  the one validated piece through the Oracle and selected string blocked partial content when
  present.
- **Command**: `pytest tests/integration/m0b/test_pyrit_scorer.py -q`.
- **Observed pass**: `6 passed`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: extracted one `_candidate_response()` helper shared by message- and piece-level paths.
- **Command after refactor**: assertion/scorer focused tests plus explicit MyPy.
- **Observed result**: `16 passed`; MyPy found no issues in 7 files.

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
- **Observed pass before final delivery validation**: `15 passed`.
- **Focused type command**: explicit MyPy invocation over assertion contracts, the adapter, and their
  unit/integration tests.
- **Observed type result before final delivery validation**: `Success: no issues found in 7 source
  files`.

The corrected local delivery run also recorded `39 passed, 2 deselected` for the core non-Docker
suite and `2 passed in 59.33s` for the unchanged M0-A Docker suite.

Draft PR #7 then passed fresh `quality`, `m0a-docker`, and `m0b-pyrit` jobs on the
review-corrected Head.

## Refactor Decision

No Attack Strategy, PromptTarget, loop control, scenario asset, Benchmark Adapter, dataset, or Final
Assertion Engine was added. Those concerns would obscure the one boundary under validation and are
deferred to their owning milestones.
