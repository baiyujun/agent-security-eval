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

## Cycle 7: Run Spec to Sample Mapping

### Target Behavior

One project `ExecutionRunSpec` maps to one Inspect `Sample` with the same ID, deterministic input,
complete versioned metadata, and recoverable M0-A execution controls.

### RED

- **Test added**: `tests/unit/execution/test_inspect_backend.py::test_run_spec_maps_to_one_sample_with_recoverable_metadata`
- **Behavior asserted**: the pure mapping preserves project identity and reconstructs the original
  Run Spec without execution-side state.
- **Command**: `pytest tests/unit/execution/test_inspect_backend.py::test_run_spec_maps_to_one_sample_with_recoverable_metadata -q`
- **Observed failure**: `ModuleNotFoundError: No module named 'agentsec_eval.execution'`.
- **Failure is correct because**: no formal Inspect execution boundary existed before the test.

### GREEN

- **Minimal implementation**: added the public `Sample` mapping and Run Spec recovery functions with
  schema version, full JSON-mode Run Spec, peer canaries, and fault metadata.
- **Command**: `pytest tests/unit/execution/test_inspect_backend.py::test_run_spec_maps_to_one_sample_with_recoverable_metadata -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: the mapping remains a direct pure construction with no runtime lifecycle behavior.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Reject metadata whose schema is missing or unsupported.

## Cycle 8: Metadata Schema Enforcement

### Target Behavior

Run Spec recovery accepts only the M0-A metadata schema version written by the mapper.

### RED

- **Test added**: `tests/unit/execution/test_inspect_backend.py::test_metadata_recovery_rejects_unknown_schema`
- **Behavior asserted**: missing and future schema versions cannot be silently interpreted as the
  current contract.
- **Command**: `pytest tests/unit/execution/test_inspect_backend.py::test_metadata_recovery_rejects_unknown_schema -q`
- **Observed failure**: both cases failed with `DID NOT RAISE ValueError`.
- **Failure is correct because**: recovery restored the nested Run Spec but did not inspect its
  enclosing schema version.

### GREEN

- **Minimal implementation**: compare the metadata version with schema `1` before Pydantic model
  recovery and raise for any other value.
- **Command**: `pytest tests/unit/execution/test_inspect_backend.py -q`
- **Observed pass**: `3 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed for the single boundary check.
- **Command after refactor**: focused Pytest, Ruff check/format, and MyPy commands.
- **Observed result**: `3 passed`; Ruff clean; format clean; MyPy clean over three files.

### Next Behavior

Validate the deterministic two-service Compose fixture and its Target HTTP protocol.

## Infrastructure Validation: Deterministic Compose Fixture

This fixture is test infrastructure rather than packaged production behavior, so it followed the
approved plan's configuration and real protocol validation instead of claiming a RED/GREEN cycle.

- **Compose configuration**: machine assertions confirmed exactly `default` and `target`, no
  published ports, one `internal: true` network, and matching resource-token labels.
- **Real protocol smoke**: built and started an isolated Compose project; opened one Session; sent
  three Turns through `default`; observed the Turn 2 tool call/result; directly read the Turn 3
  effect file from `target`; closed twice; queried state with `turn == 3` and `closed == true`.
- **Cleanup**: removed only the isolated Compose project and confirmed zero containers and networks
  remained for its resource token.

## Cycle 9: Reported Effect Path

### Target Behavior

The normalized third-turn result retains the Target-reported effect path for subsequent direct
Sandbox confirmation.

### RED

- **Test added**: `tests/unit/targets/test_http_session.py::test_target_session_preserves_reported_effect_path`
- **Behavior asserted**: Target normalization does not discard the path needed by the Harness.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_preserves_reported_effect_path -q`
- **Observed failure**: `AttributeError: 'TargetTurnResult' object has no attribute 'effect_path'`.
- **Failure is correct because**: Pydantic ignored the extra wire field because no project contract
  field existed.

### GREEN

- **Minimal implementation**: added optional `effect_path` to the frozen Target Turn result.
- **Command**: `pytest tests/unit/targets/test_http_session.py::test_target_session_preserves_reported_effect_path -q`
- **Observed pass**: `1 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no conversion branch was needed; existing Pydantic normalization handles the field.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Execute and score two concurrent Docker-backed Inspect Samples without cross-Sample state.

## Cycle 10: Concurrent Inspect Success Path

### Target Behavior

Two Run Specs execute concurrently as two Inspect Samples; each retains an isolated Store, logical
Session, Docker Sandbox, Canary, effect file, trace, and structured passing Score across three
Turns.

### RED

- **Test added**: `tests/integration/m0a/test_success.py::test_two_samples_keep_sessions_stores_canaries_and_effects_isolated`
- **Behavior asserted**: the complete project-to-Inspect-to-Target-to-Scorer path satisfies the M0-A
  success criteria and leaves a discoverable EvalLog.
- **Command**: `pytest -m docker tests/integration/m0a/test_success.py -q`
- **Observed failure**: `ImportError: cannot import name 'run_m0a_validation'`.
- **Failure is correct because**: Sample mapping existed, but no formal Inspect Task, Solver, Store,
  Sandbox transport, Scorer, or Eval lifecycle had been implemented.

### GREEN

- **Minimal implementation**: added the Inspect Sandbox JSON transport, `M0ARunState`, three-turn
  Solver, tool-event conversion, direct effect confirmation, structured Harness Scorer, in-memory
  Task builder, concurrent mock-model Eval wrapper, and Docker-aware test fixtures.
- **Command**: `pytest -m docker tests/integration/m0a/test_success.py -q`
- **Observed pass**: `1 passed in 28.52s`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: changed helper annotations from broad strings to the domain Literal vocabularies and
  formatted the implementation. During GREEN debugging, real EvalLog evidence showed that Inspect
  `0.3.246` implements Docker `read_file()` through Compose copy, which cannot read this Docker
  engine's `tmpfs` mount even though the file exists inside the container. The Target effect path
  was moved to its ephemeral writable container layer, with no host mount or volume, so the public
  API can perform direct evidence collection.
- **Command after refactor**: Ruff, format, MyPy, non-Docker Pytest, the Docker success test, and
  before/after labeled Docker resource queries.
- **Observed result**: Ruff clean; format clean; MyPy clean; `19 passed, 1 deselected`; Docker
  `1 passed in 28.52s`; labeled container and network sets were empty both before and after.

### Next Behavior

Inject a post-Session-open Solver failure and prove persisted cleanup evidence plus zero Docker
resource delta.
