# Goal Document: M0-A Inspect Execution Validation

## Go / No-Go

- **Judgment**: Go
- **Reason**: the product boundary, exact Inspect version, deterministic Target protocol, Docker
  evidence source, cleanup rule, and pass/fail commands are all fixed by the approved design.

## Target Outcome

The repository contains a minimal project-owned execution contract and an automated Inspect AI
`0.3.246` validation proving two concurrent Docker-backed Samples remain isolated, each reuses one
Target Session for three turns, every observation correlates to one Run ID, and failure leaves no
new M0-A Docker resources.

## Goal Definition

- **Type**: technical validation and delivery
- **Boundary**: frozen minimal run/trace contracts, Target protocols, Inspect mapping/Solver/Scorer,
  deterministic two-service Compose fixture, unit and integration tests, CI, and M0-A report.
- **Non-goals**:
  - Campaign Controller, PyRIT, promptfoo, M0-B, M0-C, or M1.
  - Production Final Assertion Engine, complete outcome model, persistence, or real attack Agent.
  - Real model providers, API keys, public egress, real credentials, or sensitive data.
- **Deferred work**:
  - General target discovery, non-HTTP adapters, production sandbox policy, retry/resume, and durable
    artifact storage.
- **Verification rule**: all repository gates and both Docker integration paths pass from a clean
  branch, and the Draft PR Docker job passes on GitHub Actions.
- **Evidence source**: unit tests, Inspect EvalLog Samples and Scores, direct target-Sandbox file
  reads, Docker label baseline/delta snapshots, Ruff, MyPy, Pytest, and GitHub Actions.
- **Pass criteria**: every checklist item in the M0-A request is true; any failed or skipped CI
  Docker assertion makes the milestone fail.
- **Confidence note**: the deterministic Target and direct Sandbox/Docker observations test harness
  ownership without relying on model judgment or Target self-report.
- **Judgment owner**: automated tests and GitHub Actions; the report may say `PASS` only after both.

## Current State

- `main@f0680326314db766b6d5e1dea9dbf8742e70c5e7` contains the audited reference baseline.
- The throwaway spike proves only one local-Sandbox Sample and is not production code.
- The feature branch contains the approved design and Issue #3 exists.
- The host has Docker but no native Python 3.11 interpreter; final local Python 3.11 evidence may use
  a container, while GitHub Actions supplies the canonical fresh Python 3.11 environment.
- Inspect Docker concurrency and failure cleanup are the highest-risk unknowns.

## Priority Rationale

- Lock project contracts and dependency direction before runtime code to prevent Inspect types from
  leaking into `domain` or `targets`.
- Prove the success path before fault injection so cleanup failures are diagnosable against a known
  working lifecycle.
- Defer documentation `PASS` until all evidence exists.

## Assumptions and Open Decisions

| Item | Status | Impact | Owner / Next step |
| --- | --- | --- | --- |
| Inspect `Sample` accepts versioned JSON metadata and a Compose Sandbox | confirmed by public 0.3.246 API | enables pure mapping | unit and integration tests |
| Inspect Store state is persisted on a failed Sample | assumed, testable | needed for error/close evidence | failure integration RED test |
| Compose environment interpolation reaches resource labels | assumed, testable | enables precise cleanup delta | Docker fixture test |
| GitHub runner supplies Docker Compose | confirmed by required preflight commands | CI can enforce, not skip | Docker CI job |

## Phases

### Phase 1: Contracts and pure mapping

- **Purpose**: establish stable project data and one-to-one Inspect conversion without runtime work.
- **Entry condition**: approved design committed on the feature branch.
- **Phase rules**:
  - Tests fail before production types/functions are added.
  - No Inspect type enters `domain` or `targets`.
  - No Sandbox or Session is created by the mapper.
- **Todos**:
  - [ ] Add pinned dependencies and frozen domain models.
    - **Surface**: `pyproject.toml`, `src/agentsec_eval/domain`, unit tests.
    - **Proof**: round-trip and mutation-rejection tests.
    - **Depends on**: none.
  - [ ] Add Target protocols/results and dependency-direction test.
    - **Surface**: `src/agentsec_eval/targets`, unit tests.
    - **Proof**: protocol behavior tests and AST import check.
    - **Depends on**: domain models.
  - [ ] Add pure Run Spec to Sample mapping.
    - **Surface**: `src/agentsec_eval/execution`, unit tests.
    - **Proof**: exactly one Sample, matching ID, full metadata restoration.
    - **Depends on**: pinned Inspect dependency.
- **Exit proof**: focused unit tests pass and MyPy accepts the public interfaces.
- **Stop condition**: any required interface needs an Inspect type in `domain` or `targets`.

### Phase 2: Docker success lifecycle

- **Purpose**: prove concurrent Sample, Session, Store, Sandbox, trace, and Scorer isolation.
- **Entry condition**: Phase 1 green.
- **Phase rules**:
  - Fixture services use only Python standard library and an internal network.
  - Target calls occur from the default Sandbox through the project adapter.
  - Environment evidence is read directly from the target Sandbox.
- **Todos**:
  - [ ] Add labeled two-service Compose fixture and protocol executables.
    - **Surface**: `tests/fixtures/m0a_inspect`.
    - **Proof**: Compose config validation and service health.
    - **Depends on**: none.
  - [ ] Add Inspect transport, typed Store, three-turn Solver, and harness Scorer.
    - **Surface**: `src/agentsec_eval/execution`.
    - **Proof**: successful two-Sample Docker integration test.
    - **Depends on**: Phase 1 and Compose fixture.
- **Exit proof**: two concurrent Samples have different Session/Sandbox identities and passing Scores.
- **Stop condition**: a Sample shares state or Docker resources, or evidence relies on Target text.

### Phase 3: Failure cleanup

- **Purpose**: prove rethrow, Session close, and precise Docker cleanup after Solver failure.
- **Entry condition**: success lifecycle green.
- **Phase rules**:
  - Fault injection remains execution metadata, not domain state.
  - Cleanup checks only the unique label's post-baseline resources.
  - No Docker prune or unrelated resource deletion.
- **Todos**:
  - [ ] Add the failure integration RED test and minimal fault path.
    - **Surface**: M0-A execution code and `tests/integration/m0a`.
    - **Proof**: failed Eval sample contains error/close events and resource delta reaches empty.
    - **Depends on**: Phase 2.
- **Exit proof**: bounded failure test completes with zero leaked labeled containers or networks.
- **Stop condition**: cleanup cannot be attributed to the current test token.

### Phase 4: CI, documentation, and delivery

- **Purpose**: make the proof reproducible and record only observed conclusions.
- **Entry condition**: all local tests green.
- **Phase rules**:
  - CI Docker preflight failure is fatal.
  - M0-B/M0-C/M1 remain unchanged.
  - Report says `PASS` only after real Docker execution.
- **Todos**:
  - [ ] Register markers, split CI jobs, and add explicit commands.
    - **Surface**: `pyproject.toml`, `.github/workflows/ci.yml`.
    - **Proof**: workflow syntax plus local command parity.
    - **Depends on**: Phases 1-3.
  - [ ] Update README, roadmap, manifest, and M0-A report.
    - **Surface**: required documentation files.
    - **Proof**: acceptance matrix cites real command results.
    - **Depends on**: all validation evidence.
  - [ ] Review, push, create Draft PR, and wait for CI.
    - **Surface**: Git/GitHub.
    - **Proof**: clean tree, commit SHA, Draft PR URL, passing checks.
    - **Depends on**: final local gates.
- **Exit proof**: Draft PR is open, unmerged, and all required Actions checks pass.
- **Stop condition**: any acceptance item is failed, skipped in CI, or unsupported by evidence.

## Dry-Run Findings

- The Docker fixture must precede the concrete transport; otherwise transport tests would encode an
  unverified protocol.
- Store persistence on Sample failure is deliberately tested before documentation promises it.
- The host Python gap does not weaken acceptance because the Docker test and GitHub runner provide
  Python 3.11 evidence; it must still be disclosed in the final report.
- No phase requires the throwaway spike implementation.

## Final Validation

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest -m docker tests/integration/m0a
git diff --check
```

## First Execution Step

Write failing frozen-model round-trip and mutation tests before adding the domain package.
