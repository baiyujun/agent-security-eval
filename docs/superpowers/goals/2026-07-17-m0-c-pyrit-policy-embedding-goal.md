# Goal Document: M0-C PyRIT Attack Policy Embedding Validation

## Go / No-Go

- **Judgment**: Go
- **Reason**: M0-A and M0-B are merged, PyRIT is pinned at `0.14.0`, the review explicitly approves
  M0-C, and the unresolved global-memory risk now has a bounded serialized-isolation design.

## Target Outcome

A single `ExecutionRunSpec` can drive a project-controlled multi-turn PyRIT attack through one
already-open project `TargetSession`, stop according to complete project progress states and the
exact Run budget, preserve auditable per-turn evidence, isolate and clean PyRIT memory, and return
an `AttackPolicyResult` that is explicitly separate from final security truth.

## Goal Definition

- **Type**: technical validation
- **Boundary**: Target correlation hardening, progress-state invariants, PromptTarget adapter,
  project-controlled policy loop, policy result, serialized Run-scoped PyRIT memory, deterministic
  integration proof, and an isolated CI job.
- **Non-goals**:
  - Campaign Controller, `AttackExecutor`, Scenario/Benchmark runtime, registry, importer, or data.
  - `BaseScenario`, `ScenarioCase`, `ExecutableScenarioPack`, complete `RunOutcome`, or M1 behavior.
  - Production Final Assertion Engine or promotion of the M0-A Harness.
  - Parallel PyRIT policy execution inside one process.
- **Deferred work**:
  - Worker/process isolation for truly parallel PyRIT policies.
  - The `ScenarioCase -> ExecutionRunSpec` compilation boundary.
  - Production artifact persistence and final assertion ownership.
- **Verification rule**: focused RED/GREEN tests and full repository gates prove every approved
  state transition, memory/trace/correlation invariant, failure cleanup path, and truth-separation
  example against PyRIT `0.14.0`.
- **Evidence source**: real PyRIT public lifecycle calls and models, temporary SQLite memory, fake
  project Target Sessions, deterministic adversarial targets and Oracles, Canonical Trace events,
  Docker regression tests, and GitHub Actions.
- **Pass criteria**: all M0-C acceptance tests pass; existing quality, M0-A Docker, and M0-B jobs do
  not regress; no protected reference or scenario surface changes.
- **Confidence note**: the proof covers concurrent callers through safe serialization, not overlap
  of the PyRIT critical section. That limitation follows directly from the audited global singleton.
- **Judgment owner**: automated tests and CI followed by PR review.

## Current State

- Latest `main` is `946d2cd`, containing M0-A, M0-B, and the independently merged A/C asset
  inventory.
- Baseline passes Ruff, formatting, MyPy, 39 core tests, 15 M0-B tests, and 2 M0-A Docker tests.
- `AssertionBackedPyRITScorer` preserves full project decisions and exposes only policy feedback.
- The native PyRIT loop cannot stop on false terminal states.
- CentralMemory has no public per-Run deletion API and several runtime components resolve it
  dynamically.
- JSON Target responses are not yet correlated to the active Session or strictly increasing turn.

## Plan Rewrite Notes

| Existing item | Decision | Reason |
|---|---|---|
| Native RedTeamingAttack loop | replace | It conflates boolean success with stopping. |
| M0-B scorer | keep | It is the trusted translation boundary and already protects feedback. |
| Conversation IDs plus labels | strengthen | Keep both, but add exclusive temporary memory lifecycle. |
| Concurrent PyRIT execution | rewrite | Concurrent callers are supported through serialization; overlap is deferred. |
| Full final assertion | remove | A deterministic fake belongs only in the acceptance test. |

## Drift Diagnosis

- **Goal drift**: implementing scenario assets or a Campaign Controller would not prove the policy
  boundary.
- **Phase drift**: memory isolation must be proven before claiming concurrent Run safety.
- **Validation drift**: distinct conversation IDs alone do not prove cleanup or AttackResult
  isolation.
- **Compatibility drift**: subclass behavior must be locked to PyRIT `0.14.0` extension points.
- **Cleanup drift**: resetting a user's existing CentralMemory would violate the project boundary;
  the private memory subclass must be restored and cleared independently.

## Priority Rationale

- Harden correlation and decision invariants before the policy consumes them.
- Prove the PromptTarget path before adding the turn controller.
- Treat memory as a lifecycle boundary, not a final integration detail.

## Assumptions and Open Decisions

| Item | Status | Impact | Owner / Next step |
|---|---|---|---|
| PyRIT version | confirmed | All protected API contracts target `0.14.0` | M0-C tests |
| Memory concurrency | confirmed | Serialize the PyRIT critical section in-process | `PyRITMemoryScope` |
| Target lifecycle owner | confirmed | Policy receives an open Session and never closes it | outer execution fixture |
| Final truth | confirmed | Policy result has no security verdict | deterministic acceptance test |
| Scenario assets | confirmed external | No M0-C file overlaps their model/data work | protected-surface diff check |

## Phases

### Phase 1: Trusted input invariants

- **Purpose**: prevent stale Target responses and invalid progress combinations from driving policy.
- **Entry condition**: clean M0-C worktree from latest main.
- **Phase rules**:
  - Preserve all valid M0-A and M0-B behavior.
  - Do not modify the M0-A Harness.
- **Todos**:
  - [ ] RED-test blank/extra Target fields, Session mismatch, and non-increasing turns.
    - **Surface**: Target unit tests and contracts.
    - **Proof**: focused tests fail against the current permissive behavior.
    - **Depends on**: none.
  - [ ] RED-test all state/stage and evidence uniqueness invariants.
    - **Surface**: assertions unit tests.
    - **Proof**: each illegal combination raises `ValidationError` after implementation.
    - **Depends on**: none.
- **Exit proof**: focused suites and existing M0-A/M0-B tests pass.
- **Stop condition**: hardening rejects a previously valid committed fixture.

### Phase 2: PyRIT target and policy contracts

- **Purpose**: route real PyRIT messages through one project Session and return typed policy state.
- **Entry condition**: Phase 1 is green.
- **Phase rules**:
  - PyRIT imports remain under `integrations/pyrit`.
  - No second Target or controller may be created.
- **Todos**:
  - [ ] Drive `TargetSessionPromptTarget` from real public PromptTarget sends.
    - **Surface**: PyRIT adapter and unit tests.
    - **Proof**: same Session, lineage, correlation, and trace assertions pass.
    - **Depends on**: Phase 1.
  - [ ] Drive immutable `AttackPolicyResult` and turn/stop contracts.
    - **Surface**: result module and unit tests.
    - **Proof**: serialization and invalid-combination tests pass.
    - **Depends on**: Phase 1.
- **Exit proof**: adapter and result tests use real PyRIT models with no attack loop.
- **Stop condition**: the adapter requires a Campaign or scenario type.

### Phase 3: Project stopping and memory lifecycle

- **Purpose**: prove the complete single-Run policy and safe concurrent callers.
- **Entry condition**: Phase 2 contracts are green.
- **Phase rules**:
  - Override only the pinned `_perform_async()` loop.
  - Use `ExecutionBudget.max_turns` with no second default.
  - Hold the memory lock for component construction, execution, snapshot, cleanup, and restore.
- **Todos**:
  - [ ] RED-test immediate terminal stops, exact budget, feedback separation, and complete turns.
    - **Surface**: policy integration tests.
    - **Proof**: native behavior fails false-terminal assertions before the project loop exists.
    - **Depends on**: Phase 2.
  - [ ] RED-test memory isolation, restoration, cleanup, and error paths.
    - **Surface**: memory scope and concurrent integration tests.
    - **Proof**: each Run artifact contains only its label, messages, scores, evidence, and result.
    - **Depends on**: policy loop.
  - [ ] Prove PyRIT failure and final security failure can disagree.
    - **Surface**: deterministic integration test only.
    - **Proof**: `TERMINAL_BLOCKED` plus PyRIT `FAILURE` plus fake final `true` assertion.
    - **Depends on**: complete trace.
- **Exit proof**: all approved M0-C acceptance scenarios pass against real PyRIT `0.14.0`.
- **Stop condition**: concurrency would require unsynchronized CentralMemory rebinding.

### Phase 4: Delivery evidence

- **Purpose**: make the bounded validation reproducible and regression-safe.
- **Entry condition**: all M0-C focused tests pass.
- **Phase rules**:
  - Keep PyRIT in its optional dependency extra.
  - Do not touch reference, asset, dataset, or M0-A Harness files.
- **Todos**:
  - [ ] Add isolated `m0c-pyrit` CI execution and static checks.
    - **Surface**: CI and MyPy configuration.
    - **Proof**: all four jobs pass on the PR Head.
    - **Depends on**: Phase 3.
  - [ ] Record design, test evidence, limitations, and roadmap status.
    - **Surface**: M0-C development and TDD docs.
    - **Proof**: commands and exact results are current; no production-backend claim appears.
    - **Depends on**: final verification.
- **Exit proof**: clean diff, local gates, remote CI, and scope audit pass.
- **Stop condition**: any required edit overlaps a protected parallel-work surface.

## Dry-Run Findings

- A per-Run SQLite instance cannot simply be constructed because PyRIT's concrete memory class is
  itself a singleton. A private subclass provides an integration-owned singleton that can be reset
  safely under the process lock.
- Scorer memory access is dynamic, so constructing objects under separate bindings is insufficient;
  the lock must cover the entire policy execution.
- Target closure cannot be hidden in the PromptTarget because the outer execution layer owns the
  Session and Docker lifecycle.

## Final Validation

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest -m docker tests/integration/m0a
pytest tests/unit/integrations/pyrit tests/integration/m0b tests/integration/m0c
git diff --check
```

## First Execution Step

Write failing Target contract and correlation tests before changing production models.
