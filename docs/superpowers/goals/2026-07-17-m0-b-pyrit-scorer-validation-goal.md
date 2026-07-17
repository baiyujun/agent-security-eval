# Goal Document: M0-B Assertion-Backed PyRIT Scorer Validation

## Go / No-Go

- **Judgment**: Go
- **Reason**: M0-A is merged and the approved M0-B scope has a bounded runtime boundary, a pinned
  PyRIT release, and seven executable acceptance criteria.

## Target Outcome

A project-owned, PyRIT-independent Progress Oracle decision is translated by one
`AssertionBackedPyRITScorer` into PyRIT `0.14.0` true/false semantics without losing terminal,
invalid-run, evidence, or Run identity state.

## Goal Definition

- **Type**: technical validation
- **Boundary**: Progress decision contract, Oracle protocol, PyRIT scorer adapter, minimal existing
  domain-contract hardening, focused integration proof, optional dependency, CI, and evidence docs.
- **Non-goals**:
  - PyRIT Attack Strategy, PromptTarget, Attack Policy, Campaign Controller, or CentralMemory
    isolation claims.
  - Final Assertion Engine, `BaseScenario`, `ScenarioCase`, Scenario Registry, datasets, importers,
    or Benchmark Adapter.
  - Any new behavior in `m0a_harness.py` or promotion of the M0-A Harness.
- **Deferred work**:
  - M0-C reads terminal metadata and actually stops the attack loop.
  - A separate post-PR-#5 update records the PyRIT validation result in `references/manifest.yaml`.
- **Verification rule**: all seven acceptance tests, dependency-boundary tests, existing M0-A tests,
  Ruff, formatting, MyPy, the dedicated M0-B CI job, and the unchanged M0-A Docker job pass.
- **Evidence source**: public PyRIT `0.14.0` types, deterministic test Oracle/Mock Receiver, real
  `Score` objects, concurrent scorer calls, and GitHub Actions.
- **Pass criteria**: every approved state maps exactly; cross-Run decisions become explicit
  `INVALID_RUN`; no assertions module imports PyRIT; no excluded surface is changed.
- **Confidence note**: the compatibility proof uses the pinned release and real PyRIT models, but
  deliberately does not claim Attack Strategy or process-global memory isolation.
- **Judgment owner**: automated tests and CI, followed by PR review.

## Current State

- `main` is `69328a6` with M0-A execution contracts and passing CI.
- `ExecutionRunSpec`, `ExecutionScenarioSpec`, and `CanonicalTraceEvent` are project-owned.
- Existing frozen models reject mutation but still accept extra fields and blank IDs.
- PyRIT is not installed by the core package; audited development sources are not a stable API.
- Scenario/Benchmark work continues independently in Draft PR #5.

## Priority Rationale

- Freeze the project decision semantics before importing PyRIT so the adapter cannot define truth.
- Prove the boolean-loss problem before any Attack Policy work.
- Keep the heavy PyRIT dependency and tests isolated from the core quality job.

## Assumptions and Open Decisions

| Item | Status | Impact | Owner / Next step |
|---|---|---|---|
| PyRIT release | confirmed | Adapter targets `pyrit==0.14.0` only | M0-B |
| Full decision in scalar metadata | confirmed | Store versioned JSON plus flat control fields | M0-B |
| Budget exhaustion | confirmed deferred | Scorer does not own turn stopping | M0-C |
| Scenario asset schema | confirmed deferred | No scenario or dataset types in this branch | Scenario line |
| `references/manifest.yaml` | confirmed deferred | Avoid the only known shared-file conflict | After PR #5 |

## Phases

### Phase 1: Contract hardening

- **Purpose**: make durable inputs reject unknown fields and blank primary IDs.
- **Entry condition**: clean M0-B worktree from latest main.
- **Phase rules**:
  - Do not add complete scenario entities or format-specific IDs.
  - Preserve serialized field names and existing valid behavior.
- **Todos**:
  - [ ] Add RED tests for extra fields and whitespace-only IDs.
    - **Surface**: `tests/unit/domain/test_models.py`.
    - **Proof**: tests fail against current models for the intended reason.
    - **Depends on**: none.
  - [ ] Add `extra="forbid"` and a minimal non-empty ID annotation.
    - **Surface**: `src/agentsec_eval/domain/models.py`.
    - **Proof**: focused domain suite passes.
    - **Depends on**: RED evidence.
- **Exit proof**: existing round trips pass and invalid inputs raise `ValidationError`.
- **Stop condition**: valid M0-A fixtures require a compatibility migration.

### Phase 2: Project Progress Oracle boundary

- **Purpose**: define project truth without importing PyRIT.
- **Entry condition**: hardened base contracts are green.
- **Phase rules**:
  - `OBJECTIVE_ACHIEVED` requires at least one evidence ID.
  - Budget and policy stopping are not states owned here.
- **Todos**:
  - [ ] Drive `ProgressState`, `ProgressDecision`, and `ProgressOracle` from tests.
    - **Surface**: `agentsec_eval.assertions` and unit tests.
    - **Proof**: serialization, terminal semantics, and evidence invariant tests pass.
    - **Depends on**: Phase 1.
  - [ ] Add an AST dependency test forbidding PyRIT imports.
    - **Surface**: assertions dependency test.
    - **Proof**: source scan passes.
    - **Depends on**: assertions package exists.
- **Exit proof**: the assertions package is independently importable without PyRIT.
- **Stop condition**: a decision requires a scenario-asset type or PyRIT model.

### Phase 3: PyRIT adapter compatibility

- **Purpose**: preserve project state while satisfying PyRIT true/false contracts.
- **Entry condition**: Phase 2 contracts are green.
- **Phase rules**:
  - Bind Run ID in the scorer constructor; never infer it from response text.
  - Map only `OBJECTIVE_ACHIEVED` to `True`.
  - Convert cross-Run Oracle output to explicit `INVALID_RUN` without copying its evidence.
- **Todos**:
  - [ ] RED-test `AttackScoringConfig` compatibility and all four mappings.
    - **Surface**: integration unit tests with PyRIT `0.14.0`.
    - **Proof**: imports fail before the adapter exists, then exact Score assertions pass.
    - **Depends on**: optional dependency available.
  - [ ] Implement the one-way scorer adapter.
    - **Surface**: `agentsec_eval.integrations.pyrit.scorer`.
    - **Proof**: real PyRIT `Score` values and metadata round-trip the project decision.
    - **Depends on**: RED evidence.
  - [ ] Prove two concurrent scorer instances remain Run-bound.
    - **Surface**: `tests/integration/m0b`.
    - **Proof**: each score contains only its bound Run and evidence IDs.
    - **Depends on**: scorer mapping.
- **Exit proof**: all seven acceptance criteria pass without running an Attack Strategy.
- **Stop condition**: compatibility requires a PromptTarget, Attack Policy, or global memory claim.

### Phase 4: Delivery evidence

- **Purpose**: make the bounded proof reproducible without burdening core installs.
- **Entry condition**: all focused tests pass.
- **Phase rules**:
  - PyRIT stays in an optional extra and a separate CI job.
  - Do not modify `references/manifest.yaml` or M0-A Harness code.
- **Todos**:
  - [ ] Add the `pyrit` extra and `m0b-pyrit` CI job.
    - **Surface**: `pyproject.toml`, `.github/workflows/ci.yml`.
    - **Proof**: install and focused tests pass in isolation.
    - **Depends on**: Phase 3.
  - [ ] Record scope, mappings, evidence, and limitations.
    - **Surface**: M0-B development report, roadmap, and TDD evidence.
    - **Proof**: docs cite exact commands and do not claim M0-C behavior.
    - **Depends on**: final results.
- **Exit proof**: Draft PR has passing `quality`, `m0a-docker`, and `m0b-pyrit` jobs.
- **Stop condition**: any excluded file or scenario asset must change.

## Dry-Run Findings

- PyRIT `Score.score_metadata` permits scalar values only, so the complete project decision must be
  serialized as a versioned JSON string plus flat control fields.
- Public `Scorer.score_async()` writes to process-global CentralMemory. The focused compatibility
  test may initialize in-memory storage, but M0-B must not interpret that as memory isolation proof.
- The only planned overlap with Draft PR #5 was removed by deferring `references/manifest.yaml`.

## Final Validation

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest -m docker tests/integration/m0a
pytest tests/integration/m0b
git diff --check
```

## First Execution Step

Write failing tests that reject unknown fields and whitespace-only durable IDs.
