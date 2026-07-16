# Hai TDD: M0-A Inspect Execution Validation

## Cycle 1: Frozen Run Contract

### Target Behavior

An `ExecutionRunSpec` round-trips through stable JSON and rejects mutation after construction.

### RED

- **Test added**: `tests/unit/domain/test_models.py::{test_execution_run_spec_round_trips_stable_json,test_execution_run_spec_is_frozen}`
- **Behavior asserted**: project run contracts serialize deterministically and are immutable.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed failure**: `ModuleNotFoundError: No module named 'agentsec_eval.domain'`.
- **Failure is correct because**: the new project-owned domain boundary did not exist; test imports and
  Pydantic were otherwise valid.

### GREEN

- **Minimal implementation**: added five frozen Pydantic models and package exports.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed pass**: `2 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed for the minimal five-model slice.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Positive execution budgets and canonical trace invariants.

## Cycle 2: Trace Invariants

### Target Behavior

Budgets require positive limits; canonical trace events round-trip through JSON; a trace rejects an
empty list, wrong Run ID, duplicate event ID, or non-increasing sequence.

### RED

- **Test added**: budget and trace cases in `tests/unit/domain/test_models.py`.
- **Behavior asserted**: minimal run limits and trace identity/order are enforced by project code.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed failure**: `ImportError: cannot import name 'CanonicalTraceEvent'`.
- **Failure is correct because**: the frozen run types existed, but trace contracts and validation had
  not been implemented.

### GREEN

- **Minimal implementation**: added positive budget fields, literal event/strength vocabularies,
  JSON-only trace payloads, and `validate_trace`.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed pass**: `10 passed`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: moved `Sequence` to `collections.abc` and removed an unnecessary MyPy ignore after
  quality checks identified both issues.
- **Command after refactor**: focused Pytest, Ruff check/format, and MyPy commands.
- **Observed result**: `10 passed`; Ruff clean; format clean; MyPy clean over three files.

### Next Behavior

Inspect-independent Target Session protocols and HTTP session adapter behavior.

## Cycle 3: Target Dependency Boundary

### Target Behavior

The project Target package exists and contains no `inspect_ai` import.

### RED

- **Test added**: `tests/unit/targets/test_dependency_boundary.py::test_targets_package_does_not_import_inspect`
- **Behavior asserted**: Target contracts and adapters remain independent of the Inspect runtime.
- **Command**: `pytest tests/unit/targets/test_dependency_boundary.py -q`
- **Observed failure**: `AssertionError: targets package must contain Python modules`.
- **Failure is correct because**: the Target package had not been created, and the AST import scan
  itself executed successfully.

### GREEN

- **Minimal implementation**: created the Target package with an empty public API.
- **Command**: `pytest tests/unit/targets/test_dependency_boundary.py -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed for the package boundary.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Open one logical Session and reuse its ID for every Turn.

## Cycle 4: Session Reuse

### Target Behavior

One `open_session()` call creates one logical Session whose ID and request path are reused across
multiple Turn requests.

### RED

- **Test added**: `tests/unit/targets/test_http_session.py::test_target_session_reuses_session_id`
- **Behavior asserted**: two sends retain the opened Session ID and address the same Session path.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_reuses_session_id -q`
- **Observed failure**: `ImportError: cannot import name 'JsonHttpTargetAdapter'`.
- **Failure is correct because**: the Target package existed, but no protocol or adapter behavior
  had been implemented.

### GREEN

- **Minimal implementation**: added project protocols, a frozen Turn result, and a JSON adapter that
  opens one Session and routes sends through its retained ID.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_reuses_session_id -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed for the minimal lifecycle slice.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Normalize the Fake Target's tool-call and tool-result record.

## Cycle 5: Tool Result Normalization

### Target Behavior

A Turn response containing a simulated tool call and result becomes a frozen project-native
`TargetToolCall`.

### RED

- **Test added**: `tests/unit/targets/test_http_session.py::test_target_session_normalizes_tool_call_and_result`
- **Behavior asserted**: JSON tool-call arguments and result are represented by a project contract.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_normalizes_tool_call_and_result -q`
- **Observed failure**: `ImportError: cannot import name 'TargetToolCall'`.
- **Failure is correct because**: Session sends worked, but the normalized tool contract did not
  exist.

### GREEN

- **Minimal implementation**: added frozen `TargetToolCall` and tuple normalization on
  `TargetTurnResult`.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_normalizes_tool_call_and_result -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: Pydantic validation already performs the required JSON-to-contract conversion.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Close the logical Session idempotently.

## Cycle 6: Idempotent Session Close

### Target Behavior

Calling `TargetSession.close()` more than once sends exactly one close request.

### RED

- **Test added**: `tests/unit/targets/test_http_session.py::test_target_session_close_is_idempotent`
- **Behavior asserted**: repeated cleanup does not repeat the Target-side close effect.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_close_is_idempotent -q`
- **Observed failure**: `NotImplementedError` from `_JsonHttpTargetSession.close()`.
- **Failure is correct because**: the concrete Session intentionally had no close behavior before
  this test.

### GREEN

- **Minimal implementation**: retained a per-Session closed flag and sent the close request only
  until the first successful response.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_close_is_idempotent -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed; state remains instance-scoped and minimal.
- **Command after refactor**: `pytest tests/unit/targets -q` plus focused Ruff and MyPy checks.
- **Observed result**: `4 passed`; Ruff clean; format clean; MyPy clean over five files.

### Next Behavior

Pure one-to-one mapping between `ExecutionRunSpec` and Inspect `Sample` metadata.
