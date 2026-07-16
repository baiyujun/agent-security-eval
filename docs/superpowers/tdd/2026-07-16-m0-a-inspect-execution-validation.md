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

## Cycle 11: Injected Failure Cleanup

### Target Behavior

When a selected Sample raises immediately after opening its Target Session, Inspect records the
Sample error, the project Store persists `session_opened`, `harness_error`, and `session_closed`, and
no new token-labeled container or network remains after a bounded wait.

### RED

- **Test added**: `tests/integration/m0a/test_failure_cleanup.py::test_solver_failure_closes_session_and_removes_new_resources`
- **Behavior asserted**: the explicit failure control exercises project cleanup and Inspect Sandbox
  cleanup without pruning or inspecting unrelated Docker resources.
- **Command**: `pytest -m docker tests/integration/m0a/test_failure_cleanup.py -q`
- **Observed failure**: `AssertionError: assert None is not None` for `samples[0].error` after the
  untested active-failure branch had been removed.
- **Failure is correct because**: the Run completed all three Turns successfully, while the test's
  `finally` still confirmed zero new labeled Docker resources.

### GREEN

- **Minimal implementation**: restored one metadata-gated `RuntimeError` immediately after
  `session_opened`; the existing exception and `finally` paths recorded error/close evidence and
  rethrew to Inspect.
- **Command**: `pytest -m docker tests/integration/m0a/test_failure_cleanup.py -q`
- **Observed pass**: `1 passed in 27.07s`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no production refactor was needed. Test helpers snapshot only exact token-labeled
  container/network IDs and poll their delta for at most 30 seconds.
- **Command after refactor**: Ruff, format, MyPy, and non-Docker Pytest.
- **Observed result**: Ruff clean; format clean; MyPy clean; `19 passed, 2 deselected`.

### Next Behavior

Run both Docker paths together, then wire CI and evidence documentation to the verified commands.

## Cycle 12: Unique Batch Identities

### Target Behavior

M0-A rejects duplicate Run IDs or Canaries before constructing Inspect Samples.

### RED

- **Test added**: duplicate identity tests in `tests/unit/execution/test_m0a_harness.py`.
- **Behavior asserted**: peer-Canary isolation and Sample identity cannot be ambiguous or vacuous.
- **Command**: `pytest tests/unit/execution/test_m0a_harness.py -q`
- **Observed failure**: both cases failed with `DID NOT RAISE ValueError`.
- **Failure is correct because**: `build_m0a_task()` accepted both duplicate sets.

### GREEN

- **Minimal implementation**: compare Run-ID and Canary list cardinality with their sets before
  Sample construction.
- **Command**: `pytest tests/unit/execution/test_m0a_harness.py -q`
- **Observed pass**: `2 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor needed.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Prevent Session cleanup errors from replacing a primary Solver error.

## Cycle 13: Cleanup Error Adjudication

### Target Behavior

Session close returns its failure to the Solver for logging and adjudication instead of raising from
inside `finally` and masking an active exception.

### RED

- **Test added**: `test_attempt_session_close_returns_failure_for_solver_adjudication`.
- **Behavior asserted**: the cleanup boundary returns the close error without throwing it.
- **Command**: focused Pytest for the new test.
- **Observed failure**: `ImportError: cannot import name '_attempt_session_close'`.
- **Failure is correct because**: close was still awaited unguarded in the Solver's `finally` block.

### GREEN

- **Minimal implementation**: added `_attempt_session_close`, tracked the primary error, recorded
  cleanup failures separately, and propagated a cleanup error only when no primary error exists.
- **Command**: `pytest tests/unit/execution/test_m0a_harness.py -q`
- **Observed pass**: `3 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: cleanup event-write errors follow the same primary-error preservation rule.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Re-observe the real Docker container identity throughout every Turn.

## Cycle 14: Per-Turn Sandbox Observation

### Target Behavior

Each Sample stores one initial and six per-Turn public Sandbox connection observations, and every
observation identifies the same Docker container.

### RED

- **Test added**: Store assertions in the two-Sample Docker success test.
- **Behavior asserted**: same-Sandbox proof uses repeated public observations rather than copied
  literals.
- **Command**: `pytest -m docker tests/integration/m0a/test_success.py -q`
- **Observed failure**: `KeyError: 'M0ARunState:sandbox_observations'`.
- **Failure is correct because**: the Solver captured the container identity only once.

### GREEN

- **Minimal implementation**: call `sandbox("default").connection()` initially and before/after
  every Turn, persist all seven IDs, and use the current observation in canonical events.
- **Command**: `pytest -m docker tests/integration/m0a/test_success.py -q`
- **Observed pass**: `1 passed in 28.93s`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: centralized public connection validation in `_sandbox_container_id`.
- **Command after refactor**: the same Docker test.
- **Observed result**: remained green.

### Next Behavior

Witness labeled Docker resources while Eval is active, then prove their disappearance.

## Cycle 15: Resource Lifecycle Witness

### Target Behavior

The cleanup test must observe token-labeled containers and networks during Eval before accepting an
empty post-Eval resource delta.

### RED

- **Test added**: runtime resource-observer use in `test_failure_cleanup.py`.
- **Behavior asserted**: missing labels cannot make empty baseline/post snapshots pass vacuously.
- **Command**: `pytest -m docker tests/integration/m0a/test_failure_cleanup.py -q`
- **Observed failure**: `ImportError: cannot import name 'observe_new_resources_during'`.
- **Failure is correct because**: only before/after snapshots existed.

### GREEN

- **Minimal implementation**: a test-only monitor thread polls exact token labels during the main
  thread's real Eval, accumulates observed IDs, and propagates observer failures.
- **Command**: `pytest -m docker tests/integration/m0a/test_failure_cleanup.py -q`
- **Observed pass**: `1 passed in 27.96s`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: the final failure test runs two concurrent failed Samples so one proves normal
  `session_closed` and the other proves a post-close transport error cannot replace the primary
  Solver error.
- **Command after refactor**: the same Docker failure test.
- **Observed result**: `1 passed in 28.27s`, after observing at least four containers and two networks.

### Next Behavior

Keep Scorer evidence failures inside the exact structured check schema.

## Cycle 16: Structured Scorer Evidence Failures

### Target Behavior

Invalid effect JSON or peer-Canary metadata yields named failed checks rather than Scorer exceptions.

### RED

- **Test added**: effect and peer evidence helper tests in `test_m0a_harness.py`.
- **Behavior asserted**: evidence parsing always produces boolean/detail check records.
- **Command**: `pytest tests/unit/execution/test_m0a_harness.py -q`
- **Observed failure**: missing `_effect_evidence_check` import during collection.
- **Failure is correct because**: effect decode and peer metadata errors still escaped the Scorer.

### GREEN

- **Minimal implementation**: added pure evidence-check helpers and guarded asynchronous Target reads
  and scans; the Scorer now returns `INCORRECT` with all required checks.
- **Command**: `pytest tests/unit/execution/test_m0a_harness.py -q`
- **Observed pass**: `5 passed`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: the success integration test now asserts overlapping Sample intervals and exact equality
  with the nine required Scorer check names.
- **Command after refactor**: focused success Docker test and all non-Docker tests.
- **Observed result**: success Docker `1 passed in 29.05s`; non-Docker `24 passed, 2 deselected`.

### Next Behavior

Run the complete final gates, commit the review fixes, push, and verify the Draft PR CI jobs.
