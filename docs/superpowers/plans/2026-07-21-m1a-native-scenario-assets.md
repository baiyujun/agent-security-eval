# M1-A Native Scenario Assets Implementation Plan

> **For agentic workers:** Execute task-by-task with a failing test before each production change.

**Goal:** Define the project-native scenario asset boundary, compile reviewed cases into existing
project execution inputs, and prove complete offline conversion for three SABER and two CodeIPI
representative cases without loading any upstream package.

**Architecture:** `scenario_assets` owns immutable project vocabulary and validation. Offline
importers consume a verified checkout marker, an existing `UpstreamLedgerRecord`, a rights decision,
and project-authored reconstruction assets, then emit a provenance-bearing `NativeScenarioPack`.
The pure compiler projects a reviewed `ScenarioCase` into an existing `ExecutionRunSpec` plus a
deterministic `CompiledRunInput`; runtime integrations consume only that projection.

**Tech Stack:** Python 3.11, Pydantic v2, SHA-256 canonical JSON, pytest, mypy, ruff.

## Global Constraints

- Upstream benchmark records remain ledger metadata, never the native scenario schema.
- No source package, runtime, setup, scorer, solution, evaluator, cleanup, payload, fixture, secret,
  or service URL is executed or copied.
- Raw reuse disposition and native conversion disposition remain independent.
- Every component carries its own `SourceProvenance`, `FieldLineage`, and rights decision.
- Agent-visible inputs exclude private verifier material; authorization and capabilities fail closed.
- All models are immutable and reject unknown fields; all output digests are deterministic.
- This plan stops after five complete representative cases and does not start Promptfoo or bulk
  conversion.

### Task 1: Define the native asset schema and static invariants

**Files:**
- Create: `src/agentsec_eval/scenario_assets/enums.py`
- Create: `src/agentsec_eval/scenario_assets/models.py`
- Create: `src/agentsec_eval/scenario_assets/validation.py`
- Create: `src/agentsec_eval/scenario_assets/__init__.py`
- Test: `tests/unit/scenario_assets/test_models.py`
- Test: `tests/unit/scenario_assets/test_validation.py`

**Interfaces:**
- `NativeScenarioPack`, `ScenarioFamily`, `BaseScenario`, `ScenarioCase`, and all supporting
  immutable models are Pydantic models with `frozen=True`, `extra="forbid"`.
- `validate_pack(pack) -> NativeScenarioPack` rejects missing roles, leaked private material,
  incomplete authorization, inconsistent provenance, duplicate IDs, and non-deterministic digest.
- IDs and relative paths are strict non-empty values; digests are lowercase SHA-256 values.

RED tests cover every required asset role, separation of normal task/objective/attack content,
all six probe/oracle categories, reset contracts, provenance/lineage/loss/review state, private
material exclusion, capability fail-closed behavior, and stable pack identity. GREEN implements
only the schema and validators; Refactor centralizes strict scalar and mapping validators.

### Task 2: Add the pure ScenarioCase compiler

**Files:**
- Create: `src/agentsec_eval/scenario_assets/compiler.py`
- Test: `tests/unit/scenario_assets/test_compiler.py`

**Interface:**
`compile_case(case: ScenarioCase, pack: NativeScenarioPack, config: RunConfiguration) -> CompiledRunInput`.

The compiler verifies that the case belongs to the pack, required capabilities are granted, the
authorization context permits every agent-visible field, and private verifier material is kept in
the oracle side. It returns the existing `ExecutionRunSpec`, an agent-visible prompt assembled from
the normal task and approved concrete attack content, case/pack provenance, and a canonical output
digest. Same case and config produce byte-identical output; missing capability or unauthorized
placement raises before an execution input is produced.

### Task 3: Define the Offline Benchmark Importer protocol

**Files:**
- Create: `src/agentsec_eval/scenario_assets/importers.py`
- Test: `tests/unit/scenario_assets/test_importers.py`

**Interfaces:**
- `VerifiedSourceCheckout` records only repository, commit, clean-state, and verification digest.
- `ImporterRequest` contains checkout, ledger record, `RightsDecision`, authored reconstruction
  assets, and deterministic `ConversionConfig`.
- `OfflineBenchmarkImporter.import_record(request) -> ImportResult` returns pack, component-level
  lineage, explicit conversion losses, output digest, and review state.

The protocol is source-agnostic and never imports upstream types. It rejects checkout/ledger
mismatches, prohibited raw reuse, unsafe source paths, missing authored reconstruction, and silent
loss. Contract tests prove a fake importer can load without SABER or Inspect Evals installed.

### Task 4: Implement complete representative SABER and CodeIPI importers

**Files:**
- Create: `src/agentsec_eval/scenario_assets/representatives.py`
- Create: `src/agentsec_eval/scenario_assets/importer_impl.py`
- Test: `tests/integration/scenario_assets/test_representative_conversion.py`

The project-authored reconstruction table defines three SABER cases (`A_info_001`, `B_info_001`,
`C_info_001`) and two CodeIPI cases (`ipi-issue-exfil-01-plain`, `ipi-benign-02-suspicious`).
Each output contains environment and fixture roles, normal task, attack objective, seed/candidate
reference, placement, authorization, capability requirements, all six probe/oracle bundles, reset,
source provenance, rights decision, field lineage, conversion losses, review state, and digest.
SABER A derives indirect delivery only from structured metadata; B is attack-free; C is a direct
user attack. CodeIPI covers malicious exfiltration and benign false-positive semantics. The tests
run importer→static validation→compiler→Inspect Sample for all five cases and assert no upstream
module is imported.

### Task 5: Full focused verification and stop

Run the scenario-assets unit/integration tests, full non-Docker suite, strict mypy, ruff, format
check, and `git diff --check`. Report source records discovered versus approved, native packs,
complete cases, environments, attack seeds, oracle bundles, conversion losses, rights-blocked
components, compiled inputs, and executable cases. Stop before Promptfoo, bulk conversion, or final
ledger generation.
