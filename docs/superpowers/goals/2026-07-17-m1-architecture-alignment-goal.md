# Goal Document: M1 Architecture Documentation Alignment

## Go / No-Go

- **Judgment**: Go.
- **Reason**: The owner decision is explicit: preserve Offline Import / Native Runtime, repair the
  conflicting documentation before M1, and treat the pinned PyRIT private-memory access as
  non-blocking technical debt.

## Target Outcome

The repository has one reviewable architecture story before M1:

```text
fixed upstream source
  -> Offline Benchmark Importer
  -> project-native Scenario Pack
  -> ScenarioCase compilation boundary
  -> project-owned execution runtime
  -> project-owned trace, oracle, and final outcome

fixed upstream runtime
  -> Upstream Replay Harness for isolated parity evidence only
  -X-> production campaign backend
```

ADR-0002, the scenario/data-assets plan, source audit, importer spike plan, current source locks,
and architecture terminology must all express that same boundary.

## Goal Definition

- **Type**: architecture quality and delivery.
- **Boundary**: migrate the still-valid PR #5 documentation onto latest `main`, reconcile it with
  merged PR #6, publish the canonical scenario/data-assets v1.1, update ambiguous ClawSentry and
  Adapter wording, and establish tracking issues.
- **Non-goals**:
  - No changes under `src/`, `tests/`, `pyproject.toml`, or `.github/workflows/`.
  - No `BaseScenario`, `ScenarioCase`, `CompiledRunInput`, importer, replay harness, registry,
    dataset, or production runtime implementation.
  - No migration of PR #5's conflicting `references/manifest.yaml` version.
  - No PyRIT compatibility refactor or dependency upgrade.
  - No start of M1-A implementation.
- **Deferred work**:
  - M1-A freezes the `ScenarioCase -> CompiledRunInput / ExecutionRunSpec` compiler boundary.
  - Offline importer implementation begins only after that boundary and per-asset rights approval.
  - PyRIT private `_memory` access moves behind a pinned-version compatibility helper later.
- **Verification rule**: architecture-term scans, link/YAML validation, diff-scope checks, project
  quality gates, human review, and GitHub CI must all pass.
- **Evidence source**: current source contracts, merged PR #6 source locks and asset inventory,
  PR #5 documentation, the v1.0 scenario plan, repository tests, and GitHub review state.
- **Pass criteria**:
  - ADR-0002 is `Proposed` and rejects long-lived external Benchmark runtime adapters.
  - v1.1 has no `executable_adapter`, `SaberExternalBenchmarkAdapter`, or
    `InspectEvalsExternalBenchmarkAdapter` production path.
  - `reuse_mode` and `asset_role` carry separate meanings.
  - S1 specifies `SaberImporterSpike` and `InspectEvalsCodeIPIImporterSpike`, with isolated upstream
    replay as optional comparison evidence.
  - ClawSentry is only a design reference; Gateway, online decisions, models, and concrete adapters
    remain rejected.
  - PR #5 is superseded without replacing current `references/manifest.yaml` or source locks.
  - No production or test files change.
- **Confidence note**: the runtime and type boundaries are directly observable in current code;
  source provenance is fixed in merged, reviewed YAML and inventory documents.
- **Judgment owner**: repository reviewers accept ADR-0002 and v1.1; CI verifies mechanical quality.

## Current State

- `main@e954677b53a51a2ce7505b0730bae77daebc5686` contains M0-A/B/C and merged PR #6.
- Draft PR #5 is open, conflicting, and based on older `main`; its ADR says `Accepted` despite not
  being merged.
- The external v1.0 scenario plan defines `executable_adapter`, long-lived external Adapter spikes,
  and Adapter-oriented readiness states.
- Current `ExecutionScenarioSpec` explicitly says full `BaseScenario` and `ScenarioCase` belong to a
  future scenario-assets boundary and must be compiled/materialized to `ExecutionRunSpec`.
- Current A/C ingestion design already enforces offline, fail-closed conversion and project-native
  drafts; it does not implement an external Benchmark runtime adapter.
- ClawSentry is fixed at
  `b5fe3a764e10e78f7fd5799cb9438896cdb60096`; current manifest accepts only event/trajectory
  semantics as `DESIGN_REFERENCE` and rejects Gateway, online models, and concrete adapters.
- Baseline verification: Ruff, format, MyPy passed; non-Docker tests reported
  `107 passed, 2 deselected`.

## Plan Rewrite Notes

| Existing item | Decision | Reason |
| --- | --- | --- |
| PR #5 ADR | keep and update | The boundary is correct; lifecycle status must become `Proposed`. |
| PR #5 source audit | merge and deduplicate | Cross-source findings survive, but PR #6 owns current A/C source details. |
| PR #5 manifest | remove | It conflicts with the merged capability manifest and source-lock split. |
| PR #5 importer plan | rewrite | Preserve provenance/loss/no-runtime rules; move Terminal-Bench after the first two importers. |
| v1.0 scenario objects, coverage, oracles, and reset principles | keep selectively | They remain valid when separated from the obsolete runtime-adapter route. |
| v1.0 `import_mode` | replace | It mixes reuse mechanics with asset purpose. |
| v1.0 external runtime adapters and `ADAPTER_READY` | delete | They create a second production lifecycle and truth boundary. |
| v1.0 S1 | rewrite | S1 must validate two offline importers plus optional isolated replay. |
| PyRIT `_memory` access | defer | Exact `pyrit==0.14.0` pin and CI gate make it known, bounded debt. |

## Drift Diagnosis

- **Goal drift**: v1.0 moved from building native scenario assets to supporting several external
  Benchmark runtimes indefinitely.
- **Phase drift**: S1 validates runtime adapters before the native ScenarioCase compilation boundary.
- **Validation drift**: Adapter readiness and upstream Score capture can be mistaken for project
  execution or final-security validation.
- **Compatibility drift**: PR #5 duplicates manifest ownership that PR #6 split into capability
  decisions, source locks, and import selection.
- **Cleanup drift**: PyRIT compatibility debt is unrelated to the documentation blocker and must not
  enter this change set.

## Priority Rationale

- Freeze ownership and dependency direction before naming M1 implementation types.
- Make the canonical v1.1 and ADR agree before any importer or compiler code exists.
- Reuse the merged PR #6 evidence instead of creating a second source/provenance truth.

## Assumptions and Open Decisions

| Item | Status | Impact | Owner / Next step |
| --- | --- | --- | --- |
| Offline Import / Native Runtime | confirmed | Determines all document and dependency edits | ADR reviewer |
| v1.0 remains historical input outside Git | confirmed | v1.1 becomes the repository canonical document | documentation reviewer |
| Exact `CompiledRunInput` shape | unresolved by design | Must not be guessed in this docs-only change | M1-A |
| Raw upstream asset rights | unresolved per asset | Blocks `asset_import`, not architecture documentation | source reviewer |
| PyRIT private API replacement | deferred | Does not block M1 | compatibility issue owner |

## Phases

### Phase 1: Establish evidence and decision state

- **Purpose**: make the current conflict and selected route reviewable.
- **Entry condition**: clean latest-main worktree and green baseline.
- **Phase rules**:
  - Documentation and issue state only.
  - ADR remains `Proposed` until review.
  - Every strong claim cites current code, source locks, or an audited fixed commit.
- **Todos**:
  - [ ] Write internal, docs-vs-code, architecture, field, razor, and rewrite-disposition evidence.
    - **Surface**: `docs/superpowers/audits/`.
    - **Proof**: every P1 claim has a document and code/config reference.
    - **Depends on**: clean baseline.
  - [ ] Create the blocking architecture-alignment issue.
    - **Surface**: GitHub Issues.
    - **Proof**: issue stays open until the replacement PR merges.
    - **Depends on**: audit scope.
- **Exit proof**: route, cuts, deferred debt, and acceptance criteria have one written owner.
- **Stop condition**: stop if current code or PR #6 contradicts Offline Import / Native Runtime.

### Phase 2: Migrate and align the canonical documents

- **Purpose**: replace the conflicting documentation set without reviving PR #5's stale manifest.
- **Entry condition**: Phase 1 evidence complete.
- **Phase rules**:
  - Preserve verified wording where it still matches the anchor.
  - Remove failed v1.0 blocks; replacement coverage must come from the accepted anchor.
  - Current PR #6 source locks and inventory win over PR #5 source details.
- **Todos**:
  - [ ] Add ADR-0002 as `Proposed` and link it from the architecture index.
    - **Surface**: `docs/adr/`, `docs/architecture/README.md`.
    - **Proof**: link validation and status scan.
    - **Depends on**: Phase 1.
  - [ ] Migrate the source audit as a deduplicated evidence map.
    - **Surface**: `docs/architecture/reference-reuse-audit.md`.
    - **Proof**: every fixed source tuple matches current locks or is clearly marked audit-only.
    - **Depends on**: merged PR #6 documents.
  - [ ] Rewrite the importer spike plan around two initial offline importers.
    - **Surface**: `docs/development/importer-spike-plan.md`.
    - **Proof**: no production runtime adapter and no upstream package dependency.
    - **Depends on**: ADR-0002.
  - [ ] Publish scenario/data-assets v1.1 as the canonical plan.
    - **Surface**: `docs/architecture/scenario-data-assets-v1.1.md`.
    - **Proof**: obsolete-term scans are empty and every anchor item is represented.
    - **Depends on**: ADR and current execution contracts.
- **Exit proof**: all architecture documents show the same dependency and truth flow.
- **Stop condition**: stop if a migrated claim would require changing production code or inventing
  the M1-A type shape.

### Phase 3: Delivery and review handoff

- **Purpose**: replace Draft PR #5 safely and retain non-blocking debt visibility.
- **Entry condition**: Phase 2 documents and all local gates pass.
- **Phase rules**:
  - No force push and no direct main push.
  - Replacement PR remains reviewable; ADR is not marked `Accepted` before approval.
  - Close PR #5 only after the replacement PR exists and links back to it.
- **Todos**:
  - [ ] Create the non-blocking PyRIT compatibility issue.
    - **Surface**: GitHub Issues.
    - **Proof**: issue records exact pin and upgrade checklist.
    - **Depends on**: none.
  - [ ] Push the branch and open the replacement PR.
    - **Surface**: GitHub Pull Request.
    - **Proof**: PR targets latest `main`, CI runs, and blocking issue is linked.
    - **Depends on**: all local gates.
  - [ ] Comment on and close Draft PR #5 as superseded.
    - **Surface**: PR #5.
    - **Proof**: comment links the replacement and states why its manifest was not migrated.
    - **Depends on**: replacement PR URL.
- **Exit proof**: one current PR contains the full docs fix and PR #5 no longer competes for merge.
- **Stop condition**: do not merge until reviewers accept ADR-0002 and v1.1, then change ADR status
  to `Accepted` in the reviewed branch.

## Dry-Run Findings

- The existing `docs/m1-architecture-alignment` worktree is clean and already based on latest main;
  no new worktree is needed.
- Migrating PR #5's `references/manifest.yaml` would overwrite merged PR #6 ownership, so it is
  explicitly excluded.
- The old Terminal-Bench commit and task paths in PR #5 are superseded by
  `harbor-framework/terminal-bench-2@69671f...` and current source locks.
- The scenario plan must not define `CompiledRunInput`; it may only state the compilation boundary
  M1-A will freeze.
- The architecture-blocker issue and replacement PR can close each other; the PyRIT debt issue must
  remain independent and non-blocking.

## Final Validation

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
git diff --check
```

Additional checks must parse YAML, validate relative Markdown links, scan for banned runtime-adapter
terms in current architecture documents, compare all changed paths against the allowed scope, and
confirm the replacement PR is based on latest `origin/main`.

## First Execution Step

Write the evidence audit and v1.0 disposition table before migrating ADR or scenario-plan prose.
