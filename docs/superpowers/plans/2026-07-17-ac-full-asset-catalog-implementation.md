# A/C Full Upstream Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a typed, deterministic, fail-closed generator that discovers every approved A/C
upstream record, writes the single 1464-row metadata ledger and its derived coverage report, and
detects drift without executing or copying upstream content.

**Architecture:** `agentsec_eval.reference_catalog` owns stable models, lock verification, safe
digests, source-specific discoverers, coverage calculation, deterministic rendering, and one
`generate`/`check` CLI. Each discoverer emits validated `UpstreamLedgerRecord` objects into one
in-memory tuple; coverage and both committed outputs derive only from that tuple. Full-checkout
reconciliation is isolated from Hermetic committed-output validation. Promptfoo source extraction
and project-owned policy tables live in separate modules and meet only at record construction.

**Tech Stack:** Python 3.11, Pydantic v2, PyYAML 6.0.3, Tree-sitter 0.25.2,
tree-sitter-typescript 0.23.2, argparse, Pytest, Ruff, strict MyPy, GitHub Actions.

## Global Constraints

- The approved design is
  `docs/superpowers/specs/2026-07-17-ac-full-asset-catalog-design.md` at
  `5731102d773a6f52dadea2bd1f94e552ab2f8caa`; do not change its counts, roles, typed-output
  boundaries, or conservation equations while implementing this plan.
- Maintain one Full Upstream Ledger and one Canonical Native Scenario Collection. Do not create a
  second dataset, sample dataset, Promptfoo dataset, or copied scenario tree.
- `1464` is a ledger-row acceptance observation, not a production constant and not an executable
  scenario count.
- All initial `native_output_kind` and `native_output_id` values are JSON `null`.
- Raw reuse and native conversion remain independent dimensions.
- Do not copy upstream task text, prompts, payloads, repository fixtures, solutions, credentials,
  service URLs, evaluator labels, or implementation code into project outputs or test fixtures.
- Never import or execute upstream Python/TypeScript modules, CLIs, Dockerfiles, setup commands,
  evaluators, providers, or cleanup functions.
- Use full, clean, non-shallow, non-partial checkouts at exact locked commits. Do not add a partial
  clone fallback.
- Unit tests must be hermetic and may use only project-authored `tmp_path` or fixture content.
  Tests requiring all local reference checkouts use both `integration` and `reference_catalog`
  markers and run separately.
- Every implementation task follows RED -> GREEN -> refactor -> focused commit. Do not batch all
  source families or generated outputs into one commit.

---

## Go / No-Go

- **Judgment:** Go after this plan is reviewed.
- **Reason:** The macro design and observed source counts are approved; implementation dependencies,
  module ownership, failure behavior, source order, and evidence gates are now explicit. No product
  or architecture decision remains open.

## Target Outcome

One project-owned CLI can safely regenerate or verify the complete A/C upstream metadata ledger
from locked local checkouts. A successful run proves exact source reconciliation, deterministic
digests and rendering, record-role and conversion conservation, safe output content, and zero drift
on a second `check` run.

## Goal Definition

- **Type:** Technical delivery and reproducibility.
- **Boundary:** Implement the upstream metadata catalog package, source discoverers, coverage,
  deterministic outputs, validation-selection rename, unit/integration tests, and Draft PR checks.
- **Non-goals:** Native Scenario Asset generation; Generator/Policy Adapter implementation;
  benchmark execution; target calls; Promptfoo generation, grading, or Eval Runtime reuse.
- **Deferred work:** Semantic reconstruction under `assets/scenarios/`, evaluation-time selectors,
  and executable attack-generation adapters.
- **Verification rule:** The committed outputs pass `check` twice and all count, safety, lock,
  determinism, unit, integration, lint, format, and type gates below.
- **Evidence source:** Generated JSONL/YAML bytes, Pytest assertions, read-only Git verification,
  Ruff, strict MyPy, and `git diff --check`.
- **Pass criteria:** Every acceptance gate in this plan passes at the same commit and the Draft PR
  contains the reviewable commit sequence.
- **Confidence note:** Counts are reconciled against complete locked checkouts; hermetic tests prove
  parser and failure behavior without depending on host paths.
- **Judgment owner:** Automated gates establish mechanical correctness; specification reviewers
  approve semantic classifications and the generated ledger.

## Current State

- The approved specification is committed and pushed on `codex/ac-full-asset-catalog`.
- The repository has a strict-MyPy `src/agentsec_eval` package and no reference-catalog package,
  generated upstream index, coverage file, or native scenario assets.
- The A/C source lock contains relative checkout locators for seven benchmark/reference sources;
  Promptfoo's fixed commit and role live in `references/manifest.yaml`.
- Full local checkouts exist outside the repository, so ordinary unit tests and hosted CI cannot
  assume those paths.
- `references/import-selection/ac-seed-selection.yaml` still holds the 18 conversion-validation
  records and is renamed only after the full ledger exists.

## Plan Rewrite Notes

| Existing item | Decision | Reason |
|---|---|---|
| Task 6 source-only AST parsing | rewrite | Constant modules and `strategies/index.ts` require different import handling; one rule cannot safely parse both. |
| Promptfoo policy tables in `discovery/promptfoo.py` | split | Source extraction and project-owned classification have different change reasons and review owners. |
| Task 10 committed-output assertions in full-checkout integration | move and split | Submitted JSONL/Coverage consistency must run on Hosted CI without upstream checkouts. |
| Two-file atomic wording | rewrite | Each `os.replace` is atomic, but the pair is not an operating-system transaction across crashes. |
| Twelve phases and eleven commits | keep | Their dependency order and review boundaries still match the approved target. |

## Drift Diagnosis

- **Goal drift:** None; the target remains one deterministic full upstream ledger.
- **Phase drift:** None; Task 6 and Task 10 retain their positions and commit boundaries.
- **Validation drift:** Fixed by adding a Hermetic committed-output test to Hosted CI while keeping
  source reconciliation in the full-checkout layer.
- **Compatibility drift:** Fixed by assigning separate import contracts to constant-module and
  Registry-ID parsing.
- **Cleanup drift:** None; no unrelated refactor or new runtime/data store is introduced.

## Priority Rationale

- Models and invariants come first because every discoverer and renderer depends on one stable
  record contract.
- Safe digest, checkout, and write boundaries precede source parsing so later tasks cannot bypass
  provenance or leave partial output.
- SABER is the first vertical source slice because its 716 manifest/tree reconciliation is the
  strongest early proof that discovery is exhaustive.
- Promptfoo follows the JSON/TOML/CSV sources so AST complexity cannot block basic catalog plumbing.
- Coverage and CLI orchestration come only after every source emits the same model.

## Assumptions and Decisions

| Item | Status | Decision and impact |
|---|---|---|
| TypeScript parser | confirmed | Pin `tree-sitter==0.25.2` and `tree-sitter-typescript==0.23.2` in the `catalog` extra. Parse source nodes only; no Node or Promptfoo runtime. |
| YAML dependency | confirmed | Pin `PyYAML==6.0.3` in `catalog` and `types-PyYAML==6.0.12.20260518` in `dev`. |
| Promptfoo checkout locator | confirmed | Add only `local_checkout: ../reference-sources/promptfoo-locked-fcde2e89` to its existing manifest entry; repository, commit, role, and reuse decisions remain single-sourced there. |
| CLI surface | confirmed | Add one `agentsec-reference-catalog` command with exactly `generate` and `check` subcommands. |
| Full-checkout tests | confirmed | Mark with `integration` and `reference_catalog`; default CI excludes the latter and a dedicated command runs it where checkouts exist. |
| Two-file replacement | confirmed | Use transactional two-file replacement with staged writes, Python-level rollback, and committed-pair consistency validation. Each `os.replace` is atomic; the pair is not crash-atomic. |
| Ambiguous applicability | confirmed | Preserve JSON `null` when source evidence and approved project rules do not establish Repo/Shell, MCP, or future-domain applicability; never guess from an ID string. |

## TypeScript Parser Decision

Three options were evaluated:

1. **Direct Tree-sitter parsing from Python (selected).** It has no Node process, exposes concrete
   syntax nodes, supports fail-closed allowlisting, and remains inside the typed Python package.
2. **TypeScript compiler API through Node (rejected).** It parses accurately but introduces Node,
   package-manager, and subprocess lifecycle into the generator and risks importing Promptfoo's
   module graph.
3. **Regex/text extraction (rejected).** It cannot safely distinguish comments, strings, spreads,
   nested mappings, aliases, or computed expressions and violates the approved parser constraint.

The Tree-sitter adapter has two modes. Static Constant Module mode accepts only
string/number/boolean/null literals, arrays, object literals, spread references to allowlisted
exported constants, `as const`/`satisfies` wrappers, `Object.keys(ALLOWLISTED_OBJECT)`,
`new Set(ALLOWLISTED_ARRAY)`, spreads of that static Set, and the exact
`Array.from(new Set(ALLOWLISTED_ARRAY)).sort()` shape used by the locked constants. Its imports may
resolve only among the four explicitly approved constant modules.

Registry ID mode applies only to `src/redteam/strategies/index.ts`. It permits arbitrary static
`import` and `import type` declarations but never resolves, follows, loads, or executes them. It
locates the exported `Strategies` array and reads only literal string `id` properties. Other object
properties and their subtrees are opaque. A non-array Registry, non-object element, missing or
non-string `id`, or spread element fails closed. In either mode, any relevant parse error or changed
approved shape raises `TypeScriptShapeError`; no AST node is evaluated.

## Planned Package Layout

```text
src/agentsec_eval/reference_catalog/
|-- __init__.py                 # Public catalog contracts only
|-- enums.py                    # Closed vocabularies and role/kind sets
|-- models.py                   # Frozen Pydantic records and coverage models
|-- locks.py                    # Lock loading, Git verification, safe path resolution
|-- digest.py                   # Source-only deterministic digest algorithms
|-- validation.py               # Cross-record uniqueness and output-safety checks
|-- coverage.py                 # Counts and independent conservation
|-- rendering.py                # Stable bytes and transactional two-file replacement
|-- promptfoo_policy.py         # Typed project-owned Promptfoo policy/evidence tables
|-- generation.py               # Verify -> discover -> validate -> cover -> render orchestration
|-- cli.py                      # The generate/check command boundary
`-- discovery/
    |-- __init__.py             # Ordered discoverer factory
    |-- base.py                 # DiscoveryContext and SourceDiscoverer Protocol
    |-- typescript.py           # Narrow Tree-sitter static-literal adapter
    |-- saber.py
    |-- codeipi.py
    |-- terminal_bench.py
    |-- mcp_safetybench.py
    |-- mcpsecbench.py
    |-- promptfoo.py
    `-- references.py

tests/unit/reference_catalog/
|-- test_models.py
|-- test_locks.py
|-- test_digest.py
|-- test_validation.py
|-- test_coverage.py
|-- test_rendering.py
|-- test_generation.py
|-- test_saber_discovery.py
|-- test_codeipi_discovery.py
|-- test_terminal_bench_discovery.py
|-- test_mcp_safetybench_discovery.py
|-- test_mcpsecbench_discovery.py
|-- test_promptfoo_discovery.py
|-- test_promptfoo_policy.py
|-- test_committed_outputs.py
`-- test_reference_discovery.py

tests/fixtures/reference_catalog/promptfoo/
|-- plugins.ts
|-- codingAgents.ts
|-- frameworks.ts
|-- strategies.ts
`-- strategyIndex.ts

tests/integration/reference_catalog/
|-- conftest.py
|-- test_locked_source_reconciliation.py
`-- test_committed_catalog.py
```

## Stable Interface Contracts

`SourceAssetKind` has exactly these initial values:

```text
saber_task
codeipi_sample
terminal_bench_task_directory
mcp_safetybench_task
mcpsecbench_structured_record
mcpsecbench_taxonomy
plugin
plugin_collection
plugin_alias
strategy
strategy_preset
strategy_collection
strategy_alias
deprecated_strategy_stub
source_code
test_source
configuration
license
documentation
```

The remaining enums exactly mirror the approved design: four `RawReuseDisposition` values, ten
`NativeConversionDisposition` values, four `NativeOutputKind` values, four `StateScope` values,
two `RuntimeOwnership` values, four `GenerationDependency` values, and
`GENERATOR_ADAPTER_REUSE`, `POLICY_ADAPTER_CANDIDATE`, `DESIGN_REFERENCE`, `REJECT` reuse classes.

The Pydantic fields are fixed before any discoverer is implemented:

```python
class PromptfooEntryMetadata(FrozenModel):
    requires_target_feedback: bool | None = None
    state_scope: StateScope | None = None
    remote_inference_required: bool | None = None
    runtime_ownership: RuntimeOwnership | None = None
    reuse_classification: ReuseClassification | None = None
    plugin_collection_ids: tuple[NonEmptyText, ...] = ()
    expands_to_plugin_ids: tuple[NonEmptyText, ...] = ()
    expands_to_strategy_ids: tuple[NonEmptyText, ...] = ()
    alias_of: NonEmptyText | None = None
    generation_dependency: GenerationDependency | None = None
    repo_shell_applicable: bool | None = None
    mcp_applicable: bool | None = None
    future_domain_only: bool | None = None
    embedded_data_sources: tuple[EmbeddedDataSource, ...] = ()
    embedded_data_license_disposition: RawReuseDisposition | None = None
    grader_disposition: Literal["AUXILIARY_EVIDENCE"] | None = None


class UpstreamLedgerRecord(PromptfooEntryMetadata):
    source_project: NonEmptyText
    source_repository: NonEmptyText
    source_commit: CommitSha
    source_path: RelativePosixPath
    source_record_key: NonEmptyText
    source_record_digest: Sha256Digest
    record_role: RecordRole
    source_asset_kind: SourceAssetKind
    asset_family: NonEmptyText
    scenario_class: NonEmptyText
    category: NonEmptyText
    attack_present: bool | None
    attack_origin: NonEmptyText | None
    attack_delivery_mode: NonEmptyText | None
    raw_reuse_disposition: RawReuseDisposition
    native_conversion_disposition: NativeConversionDisposition
    conversion_reason: NonEmptyText
    native_output_kind: NativeOutputKind | None = None
    native_output_id: NonEmptyText | None = None
```

`EmbeddedDataSource` contains only repository, commit, relative POSIX path, digest, and license
disposition. `NonEmptyText`, `CommitSha`, `Sha256Digest`, and `RelativePosixPath` are constrained
Pydantic annotations, not free-form aliases.

Coverage contracts are similarly explicit:

```python
class SourceCoverage(FrozenModel):
    source_project: NonEmptyText
    discovered_total: NonNegativeInt
    indexed_total: NonNegativeInt
    record_role_counts: dict[RecordRole, NonNegativeInt]
    raw_reuse_counts: dict[RawReuseDisposition, NonNegativeInt]
    native_conversion_counts: dict[NativeConversionDisposition, NonNegativeInt]


class CoverageSummary(FrozenModel):
    source_order: tuple[NonEmptyText, ...]
    sources: tuple[SourceCoverage, ...]
    role_counts: dict[RecordRole, NonNegativeInt]
    raw_reuse_counts: dict[RawReuseDisposition, NonNegativeInt]
    native_conversion_counts: dict[NativeConversionDisposition, NonNegativeInt]
    promptfoo_summary: PromptfooSummary
    saber_summary: SaberSummary
    ledger_total: NonNegativeInt
```

`PromptfooSummary` stores the seven approved Plugin/Strategy entry counts. `SaberSummary` stores
expected/discovered/indexed total and A/B/C counts. All count dictionaries materialize zero-valued
enum keys so conservation cannot silently omit a disposition.

## Phase Route

| Phase | Reviewable result | Exit proof |
|---|---|---|
| 1 | Stable record contract | Model/validation unit tests |
| 2 | Safe provenance and transactional byte boundaries | Digest/lock/rendering unit tests |
| 3-7 | One independently tested discoverer family per commit | Source fixture tests, then locked-source reconciliation |
| 8 | Coverage from the same record tuple | Role/license/conversion conservation tests |
| 9 | One deterministic generate/check surface | Generation/CLI failure and drift tests |
| 10 | Committed 1464-row ledger and coverage | Hermetic artifact validation, full-checkout integration, and two clean checks |
| 11 | One renamed 18-record validation selection | Structured count and reference search |
| 12 | Delivery evidence | Full test matrix, clean tree, Draft PR |

## Phase Rules

| Phase | Allowed result | Not allowed yet | Exit proof | Stop condition |
|---|---|---|---|---|
| 1 | Models, enums, Protocol, invariant tests | Source parsing or output files | Focused Pytest and strict MyPy | Any approved role/output pair is ambiguous |
| 2 | Digests, lock checks, byte rendering, transactional writer | Discoverer implementation | Failure-path unit tests | A Git/path/write failure cannot fail closed |
| 3 | SABER records only | Other source families | A/B/C fixture reconciliation | Manifest/tree IDs or semantics disagree |
| 4 | CodeIPI and Terminal-Bench records | MCP or Promptfoo | Two hermetic discoverer suites | Raw fixture content is needed in output |
| 5 | MCP benchmark/taxonomy records | Promptfoo | JSON/CSV shape and taxonomy tests | Category normalization needs an unapproved guess |
| 6 | Promptfoo Source Graph plus separate typed policy | Promptfoo execution or adapters | Two-mode AST, policy-boundary, and classification tests | Any relevant Registry node requires evaluation |
| 7 | Harbor/MCP-Universe reference rows | Scenario conversion | Audited-file fixture tests | A reference is mistaken for a scenario |
| 8 | Coverage and stable YAML | CLI writes | Independent conservation tests | Counts cannot derive from one record tuple |
| 9 | In-memory build plus generate/check | Committed generated output | Drift/no-write/rollback tests | A source failure can mutate output |
| 10 | JSONL, Coverage, Hermetic pair validation, full reconciliation | Native assets | Hosted artifact test, exact counts, two checks, safe-content scan | Any committed-pair or locked count/digest differs |
| 11 | Validation-selection rename and references | Scenario content changes | Structured 18-record subset test | Approved semantics or locators change |
| 12 | Verification evidence and Draft PR | Unplanned implementation | Full matrix and clean pushed tree | Any gate fails at final HEAD |

---

### Task 1: Define models, enums, and record invariants

**Files:**
- Create: `src/agentsec_eval/reference_catalog/__init__.py`
- Create: `src/agentsec_eval/reference_catalog/enums.py`
- Create: `src/agentsec_eval/reference_catalog/models.py`
- Create: `src/agentsec_eval/reference_catalog/validation.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/__init__.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/base.py`
- Create: `tests/unit/reference_catalog/test_models.py`
- Create: `tests/unit/reference_catalog/test_validation.py`

**Interfaces:**
- Consumes: Pydantic v2 and JSON-compatible safe metadata.
- Produces: `UpstreamLedgerRecord`, `PromptfooEntryMetadata`, `SourceCoverage`,
  `CoverageSummary`, `DiscoveryContext`, `SourceDiscoverer`, and closed enums.

- [ ] **Step 1: Write failing enum and model tests**

Cover every approved enum value and reject extra fields, uppercase/short digests, absolute or
parent-traversing POSIX paths, blank source keys, mismatched Promptfoo role/kind pairs, incomplete
Strategy runtime metadata, and one-sided native output fields.

Define a local `record_values` Pytest fixture containing one valid, non-Promptfoo SABER metadata
record; every negative test changes exactly one field so failures identify the intended invariant.

```python
def test_selector_cannot_be_adapter_candidate(record_values: dict[str, object]) -> None:
    record_values.update(
        record_role="attack_generation_entry",
        source_asset_kind="plugin_collection",
        native_conversion_disposition="generator_adapter_candidate",
    )
    with pytest.raises(ValidationError, match="concrete Plugin or Strategy"):
        UpstreamLedgerRecord.model_validate(record_values)


def test_initial_native_output_fields_are_paired(record_values: dict[str, object]) -> None:
    record_values["native_output_kind"] = "scenario_asset"
    with pytest.raises(ValidationError, match="native_output"):
        UpstreamLedgerRecord.model_validate(record_values)
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_models.py tests/unit/reference_catalog/test_validation.py -q`

Expected: collection fails because `agentsec_eval.reference_catalog` does not exist.

- [ ] **Step 3: Implement the closed vocabularies**

`enums.py` defines these exact `StrEnum` classes:

```python
class RecordRole(StrEnum):
    BENCHMARK_SCENARIO = "benchmark_scenario"
    NORMAL_TASK_FIXTURE = "normal_task_fixture"
    ATTACK_TAXONOMY = "attack_taxonomy"
    ATTACK_GENERATION_ENTRY = "attack_generation_entry"
    DELIVERY_STRATEGY_ENTRY = "delivery_strategy_entry"
    IMPLEMENTATION_REFERENCE = "implementation_reference"
    SOURCE_REFERENCE = "source_reference"


class NativeOutputKind(StrEnum):
    SCENARIO_ASSET = "scenario_asset"
    GENERATOR_ADAPTER = "generator_adapter"
    POLICY_ADAPTER = "policy_adapter"
    NONE = "none"
```

Also define all approved values for `SourceAssetKind`, `RawReuseDisposition`,
`NativeConversionDisposition`, `StateScope`, `RuntimeOwnership`, `GenerationDependency`, and
`ReuseClassification`. `SourceAssetKind` contains source-record kinds, all eight approved
Promptfoo kinds, and `source_code`, `test_source`, `configuration`, `license`, and `documentation`
reference kinds.

- [ ] **Step 4: Implement frozen models and model-level invariants**

Use `ConfigDict(frozen=True, extra="forbid")`, constrained non-empty strings, and a lowercase
64-hex digest pattern. `PromptfooEntryMetadata` is a Pydantic base whose fields remain top-level
when inherited by `UpstreamLedgerRecord`, preserving the approved JSONL shape. The record-level
validator enforces:

```python
CONCRETE_ADAPTER_KINDS = {
    SourceAssetKind.PLUGIN,
    SourceAssetKind.STRATEGY,
}

NO_RUNTIME_OUTPUT_KINDS = {
    SourceAssetKind.PLUGIN_COLLECTION,
    SourceAssetKind.PLUGIN_ALIAS,
    SourceAssetKind.STRATEGY_PRESET,
    SourceAssetKind.STRATEGY_COLLECTION,
    SourceAssetKind.STRATEGY_ALIAS,
    SourceAssetKind.DEPRECATED_STRATEGY_STUB,
    SourceAssetKind.SOURCE_CODE,
    SourceAssetKind.TEST_SOURCE,
    SourceAssetKind.CONFIGURATION,
    SourceAssetKind.LICENSE,
    SourceAssetKind.DOCUMENTATION,
}
```

Only concrete Plugin/Strategy kinds can have Adapter Candidate dispositions. Benchmark and fixture
records may map only to `scenario_asset`; taxonomy/selector/reference rows may map only to `none`.
Initial records may leave both native output fields null. A non-null output requires both kind and
ID and must satisfy the role/kind table.

`SourceCoverage` validates indexed/discovered equality plus raw-reuse and native-conversion sums.
`CoverageSummary` validates that source totals and role totals equal `ledger_total`.

- [ ] **Step 5: Implement cross-record validation and the discovery Protocol**

```python
class SourceCheckout(Protocol):
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...]


@dataclass(frozen=True)
class DiscoveryContext:
    repository_root: Path
    checkouts: Mapping[str, SourceCheckout]


class SourceDiscoverer(Protocol):
    source_project: str

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...


def validate_records(
    records: Sequence[UpstreamLedgerRecord],
    *,
    require_initial_outputs: bool = True,
) -> tuple[UpstreamLedgerRecord, ...]: ...
```

`validate_records` rejects duplicate `(source_project, source_path, source_record_key)` identities,
host absolute paths, initial non-null outputs, and any unsafe text-bearing output key. It returns an
immutable tuple and never mutates records.

- [ ] **Step 6: Verify GREEN and strict typing**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_models.py tests/unit/reference_catalog/test_validation.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog tests/unit/reference_catalog/test_models.py tests/unit/reference_catalog/test_validation.py
```

Expected: model/validation tests pass and MyPy reports no issues.

- [ ] **Step 7: Commit**

```bash
git add src/agentsec_eval/reference_catalog tests/unit/reference_catalog
git commit -m "catalog: define upstream ledger models and invariants"
```

### Task 2: Add deterministic digests, lock verification, and transactional rendering

**Files:**
- Modify: `pyproject.toml`
- Modify: `references/source-locks/ac-reference-sources.yaml`
- Modify: `references/manifest.yaml`
- Create: `src/agentsec_eval/reference_catalog/digest.py`
- Create: `src/agentsec_eval/reference_catalog/locks.py`
- Create: `src/agentsec_eval/reference_catalog/rendering.py`
- Create: `tests/unit/reference_catalog/test_digest.py`
- Create: `tests/unit/reference_catalog/test_locks.py`
- Create: `tests/unit/reference_catalog/test_rendering.py`

**Interfaces:**
- Consumes: repository root, YAML source locks, verified paths, JSON values, record sequences.
- Produces: `CatalogLocks`, `VerifiedCheckout`, four digest functions, deterministic JSONL bytes,
  and transactional two-file replacement with staged writes and Python-level rollback.

- [ ] **Step 1: Add failing digest vectors**

Test canonical JSON key order and Unicode handling, raw-file SHA-256, directory-manifest order,
symlink rejection, unreadable/path-escape rejection, and Promptfoo descriptor exclusion of project
conversion judgments.

```python
def test_canonical_json_digest_ignores_object_key_order() -> None:
    assert canonical_json_digest({"b": 2, "a": 1}) == canonical_json_digest({"a": 1, "b": 2})


def test_directory_manifest_digest_rejects_symlink(tmp_path: Path) -> None:
    (tmp_path / "outside").write_text("secret", encoding="utf-8")
    root = tmp_path / "task"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="symlink"):
        directory_manifest_digest(root)
```

- [ ] **Step 2: Add failing lock tests**

Use temporary Git repositories and an injected `run_git` callable. Prove rejection of absent,
dirty, wrong-commit, wrong-remote, shallow, promisor, partial-clone-extension, and missing-object
checkouts. Prove source paths cannot be absolute, contain `..`, or escape through symlinks.

- [ ] **Step 3: Add failing deterministic and rollback rendering tests**

Assert source-order/role/path/key sorting, compact sorted-key JSON, ASCII-safe output, exactly one
trailing newline, stable repeated bytes, and restoration of the first file when the second
`os.replace` is forced to fail.

- [ ] **Step 4: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_digest.py tests/unit/reference_catalog/test_locks.py tests/unit/reference_catalog/test_rendering.py -q`

Expected: imports fail because the three modules do not exist.

- [ ] **Step 5: Pin YAML support and add the Promptfoo checkout locator**

Add:

```toml
[project.optional-dependencies]
catalog = [
  "PyYAML==6.0.3",
]

dev = [
  # existing dependencies remain
  "types-PyYAML==6.0.12.20260518",
]
```

Add `local_checkout: ../reference-sources/promptfoo-locked-fcde2e89` only to the existing Promptfoo
manifest record. Add this ordering-only list to the A/C source lock so two lock documents have one
deterministic merge order without duplicating repository or commit facts:

```yaml
catalog_source_order:
  - saber
  - inspect-evals-codeipi
  - terminal-bench-2
  - mcp-safetybench
  - mcpsecbench
  - promptfoo
  - harbor
  - mcp-universe
```

`load_catalog_locks(repository_root)` merges A/C source locks with that Promptfoo record, requires
the ordered names to equal the loaded source-key set exactly, and stores this tuple as the sole
rendering/discovery order. It does not duplicate Promptfoo repository, commit, role, or license
decisions.

- [ ] **Step 6: Implement digest functions with no policy decisions**

```python
def canonical_json_digest(value: JsonValue) -> str: ...
def raw_file_digest(path: Path) -> str: ...
def directory_manifest_digest(root: Path) -> str: ...
def promptfoo_descriptor_digest(descriptor: Mapping[str, JsonValue]) -> str: ...
```

Canonical JSON uses UTF-8, sorted keys, compact separators, and `ensure_ascii=False`. Directory
manifests recursively sort relative POSIX paths, reject every symlink/non-regular file, and hash
`path:file_sha256\n`. `digest.py` imports no enums or disposition policy.

- [ ] **Step 7: Implement lock loading and read-only Git verification**

```python
@dataclass(frozen=True)
class SourceLock:
    source_project: str
    repository: str
    commit: str
    local_checkout: Path
    audited_files: tuple[PurePosixPath, ...]


@dataclass(frozen=True)
class VerifiedCheckout:
    lock: SourceLock
    root: Path


def load_catalog_locks(repository_root: Path) -> CatalogLocks: ...
def verify_checkout(lock: SourceLock, *, repository_root: Path) -> VerifiedCheckout: ...
def verify_all_checkouts(locks: CatalogLocks, *, repository_root: Path) -> Mapping[str, VerifiedCheckout]: ...
def resolve_source_path(checkout: VerifiedCheckout, path: PurePosixPath) -> Path: ...
```

`VerifiedCheckout` exposes read-only `source_project`, `repository`, `commit`, and `audited_files`
properties delegating to `lock`, so it structurally satisfies `SourceCheckout`.

Verification runs only `git remote get-url origin`, `rev-parse HEAD`, `status --porcelain`,
`rev-parse --is-shallow-repository`, relevant `git config --get` checks, and
`GIT_NO_LAZY_FETCH=1 git rev-list --objects --missing=print HEAD`. Normalize only trailing `.git`
and `/` for remote comparison. Any missing object or output beginning `?` fails closed.

- [ ] **Step 8: Implement deterministic rendering and transactional two-file replacement**

```python
@dataclass(frozen=True)
class RenderedCatalog:
    ledger_jsonl: bytes
    coverage_yaml: bytes


def render_jsonl(
    records: Sequence[UpstreamLedgerRecord],
    *,
    source_order: Sequence[str],
) -> bytes: ...


def replace_outputs_transactionally(
    rendered: RenderedCatalog,
    *,
    ledger_path: Path,
    coverage_path: Path,
) -> None: ...
```

Stage temp files beside their targets, flush and `os.fsync`, preserve previous bytes, replace only
after both stages succeed, and restore the previous pair on a caught second-replace failure. Always
clean temp files. Each `os.replace` is individually atomic. A process crash or power loss between
the two replacements is not automatically rolled back; Task 10's Hosted Hermetic Artifact Test
detects a committed mismatched pair by recalculating Coverage from JSONL. Do not add a version
directory, symlink, database, or extra manifest. Coverage YAML rendering is added in Task 8 after
its model exists.

- [ ] **Step 9: Verify GREEN**

Run:

```bash
.venv/bin/pip install -e ".[dev,catalog]"
.venv/bin/pytest tests/unit/reference_catalog/test_digest.py tests/unit/reference_catalog/test_locks.py tests/unit/reference_catalog/test_rendering.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog tests/unit/reference_catalog
```

Expected: all focused tests and strict MyPy pass.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml references/source-locks/ac-reference-sources.yaml references/manifest.yaml src/agentsec_eval/reference_catalog tests/unit/reference_catalog
git commit -m "catalog: add deterministic digest and lock verification"
```

### Task 3: Implement SABER discovery and 716-record reconciliation

**Files:**
- Create: `src/agentsec_eval/reference_catalog/discovery/saber.py`
- Create: `tests/unit/reference_catalog/test_saber_discovery.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: verified SABER checkout, `dataset/manifest.json`, and
  `tasks/{A,B,C}/{category}/{task_id}.json` only.
- Produces: exactly one `benchmark_scenario` record per manifest task ID.

- [ ] **Step 1: Write project-authored fixture tests**

Build a three-task temporary checkout with one A, B, and C record. Assert canonical record digests,
path/key/category extraction, and these semantics:

```python
assert (a.attack_present, a.attack_origin) == (True, None)
assert b.attack_present is False
assert (c.attack_present, c.attack_origin, c.attack_delivery_mode) == (
    True,
    "user",
    "direct_user_request",
)
```

Construct the fixture discoverer with `SaberDiscoverer(expected_total=3)`. Add failures for
duplicate manifest IDs, duplicate task IDs, missing/extra files, path/ID/scenario mismatch,
malformed JSON, unknown scenario, and disagreement among expected total, manifest `counts.tasks`,
manifest IDs, and parsed task IDs. The production default remains 716. The discoverer must ignore
`tasks/pilot_tasks.json`; only the approved A/B/C glob is in scope.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_saber_discovery.py -q`

Expected: import fails because `SaberDiscoverer` does not exist.

- [ ] **Step 3: Implement `SaberDiscoverer`**

```python
@dataclass(frozen=True)
class SaberDiscoverer:
    source_project = "saber"
    expected_total: int = 716

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...
```

Read JSON as data. Reconcile the manifest ID set with parsed task IDs before creating records.
Require path scenario/category, JSON `scenario`/`category`, and ID prefix to agree. Scenario A is an
indirect-attack record with delivery taken only from its structured injection metadata; Scenario B
has `attack_present=false`; Scenario C is a direct user attack. Ambiguous origin or delivery stays
null. Every row is `review_required` plus `eligible_for_semantic_reconstruction`, with both native
output fields null. Do not retain task/setup/ground-truth content.

- [ ] **Step 4: Verify GREEN and source isolation**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_saber_discovery.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/discovery/saber.py tests/unit/reference_catalog/test_saber_discovery.py
```

Expected: fixture tests pass without reading `/root/HJY/reference-sources`.

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/reference_catalog/discovery tests/unit/reference_catalog/test_saber_discovery.py
git commit -m "catalog: discover and reconcile SABER records"
```

### Task 4: Implement CodeIPI and Terminal-Bench 2 discovery

**Files:**
- Create: `src/agentsec_eval/reference_catalog/discovery/codeipi.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/terminal_bench.py`
- Create: `tests/unit/reference_catalog/test_codeipi_discovery.py`
- Create: `tests/unit/reference_catalog/test_terminal_bench_discovery.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: CodeIPI's one JSON array and Terminal-Bench 2 top-level task directories.
- Produces: `benchmark_scenario` CodeIPI records and `normal_task_fixture` Terminal-Bench records.

- [ ] **Step 1: Write failing CodeIPI tests**

Use a minimal array with one malicious and one benign record. Assert the source key is `id`, the
digest covers the entire canonical source record, `attack_present == (not is_benign)`, delivery is
the structured `injection_vector`, and no emitted field contains `issue_text`, task description,
payload, expected action/fix, verification command, or repository file content. Reject duplicate
IDs, unknown/missing structural fields, non-array roots, and non-boolean `is_benign`.

- [ ] **Step 2: Write failing Terminal-Bench tests**

Create two top-level task directories with `task.toml` plus nested files. Assert POSIX task-key
ordering and directory-manifest digests. Reject a top-level task without `task.toml`, a task symlink,
an unreadable member, and a path escape. Ignore repository control directories such as `.git`; do
not parse or emit `instruction.md`, solution, test, Dockerfile, or fixture content.

- [ ] **Step 3: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_codeipi_discovery.py tests/unit/reference_catalog/test_terminal_bench_discovery.py -q`

Expected: both discoverers are missing.

- [ ] **Step 4: Implement both independent discoverers**

```python
class CodeIPIDiscoverer:
    source_project = "inspect-evals-codeipi"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...


class TerminalBenchDiscoverer:
    source_project = "terminal-bench-2"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...
```

CodeIPI reads only
`src/inspect_evals/ipi_coding_agent/dataset/samples.json`. Terminal-Bench discovers each immediate
directory containing `task.toml` and requires every non-control immediate directory to be a valid
task. Both use `review_required` plus `eligible_for_semantic_reconstruction`; both retain safe
metadata only and leave native output fields null.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_codeipi_discovery.py tests/unit/reference_catalog/test_terminal_bench_discovery.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/discovery/codeipi.py src/agentsec_eval/reference_catalog/discovery/terminal_bench.py tests/unit/reference_catalog/test_codeipi_discovery.py tests/unit/reference_catalog/test_terminal_bench_discovery.py
```

- [ ] **Step 6: Commit**

```bash
git add src/agentsec_eval/reference_catalog/discovery tests/unit/reference_catalog/test_codeipi_discovery.py tests/unit/reference_catalog/test_terminal_bench_discovery.py
git commit -m "catalog: discover CodeIPI and Terminal-Bench records"
```

### Task 5: Implement MCP-SafetyBench and MCPSecBench discovery

**Files:**
- Create: `src/agentsec_eval/reference_catalog/discovery/mcp_safetybench.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/mcpsecbench.py`
- Create: `tests/unit/reference_catalog/test_mcp_safetybench_discovery.py`
- Create: `tests/unit/reference_catalog/test_mcpsecbench_discovery.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: MCP-SafetyBench attack-task JSON files, MCPSecBench `data/data.json`, and the
  `data/experiments.csv` taxonomy header.
- Produces: structured MCP benchmark records plus taxonomy-only records with no runtime output.

- [ ] **Step 1: Write failing MCP-SafetyBench fixture tests**

Use project-authored JSON objects containing only shape-compatible keys. Assert recursive discovery
under `mcpuniverse/benchmark/configs/test/*/*.json`, record key
`<domain>/<filename-without-.json>`, canonical digest, category extraction from `attack_category`,
and `attack_present=true`. Reject files outside the two-level shape, duplicate record keys,
missing/blank categories, malformed JSON, and source payload fields leaking into emitted records.

- [ ] **Step 2: Write failing MCPSecBench structured/taxonomy tests**

Use a miniature structured array and CSV header. Normalize only these source-declared spelling
pairs before set subtraction:

```python
MCPSecBenchDiscoverer.CATEGORY_ALIASES = {
    "tool/service misuse via confused ai": "tool misuse via confused ai",
    "package name squatting(tools name)": "package name squatting(tool name)",
    "package name squatting(server name)": "package name squatting(server name)",
    "rug pull attack": "rug pull",
}
```

Normalize Unicode quotes, case, and whitespace before applying that exact alias table. Assert one
structured row per `data.json` item and one `attack_taxonomy` row for every CSV category absent from
the structured set. Reject duplicate structured categories, duplicate CSV categories after
normalization, missing `attack` fields, and inconsistent roots. Taxonomy rows have all attack fields
null and `native_conversion_disposition=design_reference_only`.

- [ ] **Step 3: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_mcp_safetybench_discovery.py tests/unit/reference_catalog/test_mcpsecbench_discovery.py -q`

Expected: both modules are absent.

- [ ] **Step 4: Implement both source-specific discoverers**

```python
class MCPSafetyBenchDiscoverer:
    source_project = "mcp-safetybench"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...


class MCPSecBenchDiscoverer:
    source_project = "mcpsecbench"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...
```

Structured records are `review_required` plus `eligible_for_semantic_reconstruction`. MCPSecBench
taxonomy-only rows are `review_required` plus `design_reference_only`. Do not emit MCP server
modifications, implementation code, prompts, expected results, evaluator declarations, credentials,
URLs, or experiment outcome values. Structured records use canonical JSON digests. Taxonomy-only
digests hash UTF-8 `source_path + "\n" + source_record_key + "\n" + declared_category` exactly.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_mcp_safetybench_discovery.py tests/unit/reference_catalog/test_mcpsecbench_discovery.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/discovery/mcp_safetybench.py src/agentsec_eval/reference_catalog/discovery/mcpsecbench.py tests/unit/reference_catalog/test_mcp_safetybench_discovery.py tests/unit/reference_catalog/test_mcpsecbench_discovery.py
```

- [ ] **Step 6: Commit**

```bash
git add src/agentsec_eval/reference_catalog/discovery tests/unit/reference_catalog/test_mcp_safetybench_discovery.py tests/unit/reference_catalog/test_mcpsecbench_discovery.py
git commit -m "catalog: discover MCP benchmark and taxonomy records"
```

### Task 6: Implement source-only Promptfoo TypeScript discovery

**Files:**
- Modify: `pyproject.toml`
- Create: `src/agentsec_eval/reference_catalog/promptfoo_policy.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/typescript.py`
- Create: `src/agentsec_eval/reference_catalog/discovery/promptfoo.py`
- Create: `tests/fixtures/reference_catalog/promptfoo/plugins.ts`
- Create: `tests/fixtures/reference_catalog/promptfoo/codingAgents.ts`
- Create: `tests/fixtures/reference_catalog/promptfoo/frameworks.ts`
- Create: `tests/fixtures/reference_catalog/promptfoo/strategies.ts`
- Create: `tests/fixtures/reference_catalog/promptfoo/strategyIndex.ts`
- Create: `tests/unit/reference_catalog/test_promptfoo_discovery.py`
- Create: `tests/unit/reference_catalog/test_promptfoo_policy.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: five project-authored golden TypeScript fixtures, typed project policy tables, and only
  approved locked Promptfoo source paths in integration.
- Produces: a typed `PromptfooSourceGraph`, independently validated concrete policy coverage, 291
  `attack_generation_entry` rows, and 38 `delivery_strategy_entry` rows without importing
  Promptfoo.

The module boundary is strict: `discovery/typescript.py` contains only limited AST reading and no
security/license/applicability policy; `discovery/promptfoo.py` extracts and reconciles the locked
Source Graph, then joins it to policy without housing large policy tables; `promptfoo_policy.py`
contains only frozen typed project judgments and evidence paths, with no parser, filesystem read, or
upstream execution capability.

- [ ] **Step 1: Pin the parser dependencies**

Extend the `catalog` extra exactly:

```toml
catalog = [
  "PyYAML==6.0.3",
  "tree-sitter==0.25.2",
  "tree-sitter-typescript==0.23.2",
]
```

No Node package, Promptfoo package, JavaScript runtime, or subprocess parser is added. If
`tree_sitter_typescript` lacks inline typing metadata, isolate one justified
`# type: ignore[import-untyped]` in `discovery/typescript.py`; no other catalog module may suppress
that import.

- [ ] **Step 2: Write failing two-mode AST golden tests**

The four Constant fixtures contain project-authored literal arrays/objects, approved relative
imports, imported spreads, Collection overlap, alias expansion to both Plugins and Strategies, and
accepted Strategy deduplication. Static Constant Module tests assert the extracted symbol graph and
fail on imports outside the explicit four-module allowlist, comments containing fake constants,
template strings, function calls, computed values, unresolved identifiers, or parse error nodes.

```python
def test_parser_rejects_dynamic_initializer(tmp_path: Path) -> None:
    source = tmp_path / "dynamic.ts"
    source.write_text("export const PLUGINS = loadPlugins();\n", encoding="utf-8")
    with pytest.raises(TypeScriptShapeError, match="call_expression"):
        TypeScriptStaticModule.parse(source).exported_value("PLUGINS")
```

`strategyIndex.ts` contains imports from deliberately nonexistent runtime and strategy modules,
including both `import` and `import type`, followed by a project-authored `Strategies` array with
opaque action functions. Registry ID mode must return only its literal IDs without trying to open
any imported path. Add failures for a non-array `Strategies` initializer, non-object element,
missing/non-string/duplicate `id`, spread element, and syntax error.

```typescript
import cliState from '../../cliState';
import { addHydra } from './hydra-does-not-exist';
import type { Strategy } from './types-does-not-exist';

export const Strategies: Strategy[] = [
  { id: 'basic', action: async () => [] },
  { id: 'jailbreak:hydra', action: async () => addHydra(cliState) },
];
```

- [ ] **Step 3: Write failing Promptfoo Source Graph and classification tests**

Against the miniature fixtures, assert:

- concrete IDs, Collections, and alias-only selectors are distinct source kinds;
- overlap uses `plugin_collection` precedence and emits one row;
- Collection/alias/preset/stub entries are never Adapter Candidates;
- only concrete Plugins/Strategies can be generator/policy candidates;
- `other-encodings` is `strategy_collection` plus `design_reference_only`;
- `multilingual` remains a concrete `strategy` generator candidate backed by
  `src/redteam/strategies/multilingual.ts` even though it is handled outside the main registry;
- `prompt-injection` and `jailbreak` are duplicate `strategy_alias` rows for their canonical IDs;
- `simba` is a registry-only unsupported stub;
- entry digests change when source membership/dependency flags change but not when project
  conversion wording changes; and
- `repo_shell_applicable`, `mcp_applicable`, and `future_domain_only` stay null when neither source
  evidence nor an approved mapping proves a value.

- [ ] **Step 4: Write failing typed policy-boundary tests**

In `test_promptfoo_policy.py`, assert:

- concrete Plugin policy keys equal the fixed 155-ID locked snapshot with no missing or extra key;
- concrete Strategy policy keys equal the fixed 33-ID concrete Strategy snapshot with no missing or
  extra key;
- Plugin and Strategy policy ID sets are disjoint;
- Collection, alias, preset, and stub IDs are absent from both concrete policy maps;
- every `PROMPTFOO_EVIDENCE_PATHS` key is a concrete policy ID and every value is a non-absolute,
  traversal-free `PurePosixPath`;
- every policy value is a frozen typed model and every classification dimension is mutually
  exclusive; and
- an AST import-boundary scan proves `promptfoo_policy.py` imports no Tree-sitter/discovery module,
  calls no filesystem read or subprocess API, and cannot read or execute upstream source.

- [ ] **Step 5: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_promptfoo_discovery.py tests/unit/reference_catalog/test_promptfoo_policy.py -q`

Expected: parser, discoverer, and policy imports fail.

- [ ] **Step 6: Implement the narrow two-mode Tree-sitter adapter**

```python
StaticScalar = str | int | bool | None
StaticValue = StaticScalar | tuple["StaticValue", ...] | Mapping[str, "StaticValue"]


class TypeScriptShapeError(ValueError):
    pass


@dataclass(frozen=True)
class TypeScriptStaticModule:
    path: Path
    source: bytes
    exports: Mapping[str, StaticValue]

    @classmethod
    def parse(
        cls,
        path: Path,
        *,
        allowed_imports: Mapping[str, Mapping[str, StaticValue]],
        imported_exports: Mapping[str, StaticValue] | None = None,
    ) -> TypeScriptStaticModule: ...

    def exported_value(self, name: str) -> StaticValue: ...


def extract_registry_ids(
    path: Path,
    *,
    export_name: str = "Strategies",
) -> tuple[str, ...]: ...
```

Initialize the grammar through `Language(tree_sitter_typescript.language_typescript())` and
`Parser(language)`. The golden test is the compatibility proof for the pinned 0.25.2/0.23.2 pair;
do not float either dependency independently.

Static Constant Module mode walks named AST nodes and resolves relative imports only when both the
module path and imported binding appear in `allowed_imports`. It rejects every other import,
unresolved identifier, dynamic expression, or unknown call. Registry ID mode parses the one source
file, permits arbitrary static import declarations, and neither resolves bindings nor opens imported
paths. It locates the exported array and reads only literal `id` properties; action functions,
calls, templates, and all other property subtrees are opaque. Both modes use AST nodes, never source
regexes or execution.

- [ ] **Step 7: Implement the independent typed policy module**

```python
@dataclass(frozen=True)
class PromptfooPluginPolicy:
    native_conversion_disposition: NativeConversionDisposition
    generation_dependency: GenerationDependency
    repo_shell_applicable: bool | None
    mcp_applicable: bool | None
    future_domain_only: bool | None
    embedded_data_license_disposition: RawReuseDisposition


@dataclass(frozen=True)
class PromptfooStrategyPolicy:
    native_conversion_disposition: NativeConversionDisposition
    runtime_ownership: RuntimeOwnership
    state_scope: StateScope
    requires_target_feedback: bool
    remote_inference_required: bool
    generation_dependency: GenerationDependency
    repo_shell_applicable: bool | None
    mcp_applicable: bool | None
    future_domain_only: bool | None
    embedded_data_license_disposition: RawReuseDisposition


LOCKED_CONCRETE_PLUGIN_IDS: frozenset[str] = frozenset(...)
LOCKED_CONCRETE_STRATEGY_IDS: frozenset[str] = frozenset(...)
CONCRETE_PLUGIN_POLICIES: Mapping[str, PromptfooPluginPolicy] = MappingProxyType(...)
CONCRETE_STRATEGY_POLICIES: Mapping[str, PromptfooStrategyPolicy] = MappingProxyType(...)
PROMPTFOO_EVIDENCE_PATHS: Mapping[str, tuple[PurePosixPath, ...]] = MappingProxyType(...)
```

At module import, compare each policy map to its locked concrete-ID snapshot and compare evidence
keys to their union. Raise `RuntimeError` for missing/extra keys or invalid paths. The module owns
conversion, runtime ownership, state scope, target feedback, remote dependency, applicability, and
embedded-data/license judgments. It contains no source parser or I/O. Explicit selector-rule
functions classify Collection, alias, preset, and stub Source Graph nodes without placing those IDs
in either concrete policy map. Separate Plugin and Strategy policy types ensure Strategy-only ledger
fields remain null on Plugin rows.

- [ ] **Step 8: Implement `PromptfooDiscoverer` with explicit approved surfaces**

```python
PROMPTFOO_REGISTRY_PATHS = (
    "src/redteam/constants/plugins.ts",
    "src/redteam/constants/codingAgents.ts",
    "src/redteam/constants/frameworks.ts",
    "src/redteam/constants/strategies.ts",
    "src/redteam/strategies/index.ts",
)


class PromptfooDiscoverer:
    source_project = "promptfoo"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...
```

Extract `ALL_PLUGINS`, `COLLECTIONS`, Coding Agent sets, `MCP_PLUGINS`, remote/dataset sets,
`ALIASED_PLUGIN_MAPPINGS`, `ALL_STRATEGIES`, Strategy Collections/mappings, remote/multi-turn sets,
and registry IDs into a frozen `PromptfooSourceGraph`. Compare the graph's concrete Plugin/Strategy
sets with `LOCKED_CONCRETE_PLUGIN_IDS` and `LOCKED_CONCRETE_STRATEGY_IDS` before constructing any
record. `discovery/promptfoo.py` combines Source Graph nodes with the policy module but contains no
large evidence/classification tables. Collections, aliases, presets, and stubs use the explicit
selector rules and remain outside concrete policy. `grader_disposition` is always
`AUXILIARY_EVIDENCE` when present.

The conversion partition is explicit and unit-tested: 154 concrete Plugins plus 20 concrete
Strategies are `generator_adapter_candidate`; `agentic:memory-poisoning` plus nine concrete
Strategies are `policy_adapter_candidate`; 16 Plugin Collections, 118 mapped alias-only selectors,
and six Strategy selector/runtime references are `design_reference_only`; two unmapped Plugin
aliases plus `simba` are `unsupported`; and two deprecated Strategy aliases are `duplicate`.

Raw reuse is classified independently. MIT-licensed source declarations with no embedded data or
remote-output dependency are `allowed`; entries with embedded datasets, third-party prompt sources,
or remote generation/output terms are `review_required`; `prohibited` is used only when source
evidence establishes that restriction. Every entry records the evidence paths behind that decision,
and no embedded data is copied. Evidence paths live only in `promptfoo_policy.py`; they are explicit,
never a broad repository glob, and their source content is never emitted.

- [ ] **Step 9: Verify GREEN, parser isolation, and dependency boundaries**

Run:

```bash
.venv/bin/pip install -e ".[dev,catalog]"
.venv/bin/pytest tests/unit/reference_catalog/test_promptfoo_discovery.py tests/unit/reference_catalog/test_promptfoo_policy.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/promptfoo_policy.py src/agentsec_eval/reference_catalog/discovery/typescript.py src/agentsec_eval/reference_catalog/discovery/promptfoo.py tests/unit/reference_catalog/test_promptfoo_discovery.py tests/unit/reference_catalog/test_promptfoo_policy.py
! rg -n "subprocess|node|promptfoo.*(import|require)|from promptfoo|import promptfoo" src/agentsec_eval/reference_catalog/discovery/{typescript,promptfoo}.py
! rg -n "tree_sitter|subprocess|read_text|read_bytes|open\(" src/agentsec_eval/reference_catalog/promptfoo_policy.py
```

Expected: golden tests pass, strict MyPy passes, and the prohibited runtime search has no matches.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml src/agentsec_eval/reference_catalog/promptfoo_policy.py src/agentsec_eval/reference_catalog/discovery tests/fixtures/reference_catalog/promptfoo tests/unit/reference_catalog/test_promptfoo_discovery.py tests/unit/reference_catalog/test_promptfoo_policy.py
git commit -m "catalog: discover Promptfoo source entries"
```

### Task 7: Implement Harbor and MCP-Universe reference discovery

**Files:**
- Create: `src/agentsec_eval/reference_catalog/discovery/references.py`
- Create: `tests/unit/reference_catalog/test_reference_discovery.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: each source lock's exact `audited_files` list.
- Produces: one safe raw-file-digest reference row per audited file, never a scenario row.

- [ ] **Step 1: Write failing reference tests**

Use two temporary checkouts and locks with documentation, license, config, source, and test paths.
Assert `AuditedReferenceDiscoverer` emits the configured role, assigns the deterministic reference
`SourceAssetKind`, uses `scenario_class="reference_only"`, hashes raw bytes, and leaves attack and
native output fields null. Reject duplicate/missing/a-directory audited paths and symlinks.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_reference_discovery.py -q`

- [ ] **Step 3: Implement one parameterized discoverer with two independent instances**

```python
@dataclass(frozen=True)
class AuditedReferenceDiscoverer:
    source_project: str
    record_role: RecordRole

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...


def reference_discoverers() -> tuple[AuditedReferenceDiscoverer, ...]:
    return (
        AuditedReferenceDiscoverer("harbor", RecordRole.IMPLEMENTATION_REFERENCE),
        AuditedReferenceDiscoverer("mcp-universe", RecordRole.SOURCE_REFERENCE),
    )
```

Classify by exact path role: license names -> `license`, `.md` -> `documentation`,
`pyproject.toml`/`.json`/`.gitmodules` -> `configuration`, `tests/` -> `test_source`, remaining
approved source files -> `source_code`. All rows are `raw_reuse_disposition=allowed` for raw
repository code/license metadata but `native_conversion_disposition=design_reference_only`; this
does not authorize copying those files into native assets.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_reference_discovery.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/discovery/references.py tests/unit/reference_catalog/test_reference_discovery.py
```

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/reference_catalog/discovery tests/unit/reference_catalog/test_reference_discovery.py
git commit -m "catalog: index implementation and source references"
```

### Task 8: Calculate coverage and both conservation dimensions

**Files:**
- Create: `src/agentsec_eval/reference_catalog/coverage.py`
- Create: `tests/unit/reference_catalog/test_coverage.py`
- Modify: `src/agentsec_eval/reference_catalog/rendering.py`
- Modify: `tests/unit/reference_catalog/test_rendering.py`

**Interfaces:**
- Consumes: the already validated immutable record tuple only.
- Produces: source/role/raw-reuse/native-conversion counts, Promptfoo summary, SABER split, and
  stable coverage YAML from the same records used by JSONL.

- [ ] **Step 1: Write failing coverage tests**

Generate synthetic unique records covering all roles and dispositions. Assert per-source
`discovered_total == indexed_total`, raw-reuse and native-conversion sums, role sums, Promptfoo
concrete/Collection/alias/Strategy/stub counts, and SABER A/B/C counts. Direct construction of an
inconsistent `SourceCoverage` or `CoverageSummary` must raise `ValidationError`.

```python
def test_coverage_uses_one_record_sequence(records: tuple[UpstreamLedgerRecord, ...]) -> None:
    summary = calculate_coverage(records, source_order=("saber", "promptfoo"))
    assert summary.ledger_total == len(records)
    assert sum(summary.role_counts.values()) == len(records)
```

- [ ] **Step 2: Add failing stable YAML tests**

Assert `render_coverage_yaml(summary)` preserves model/source order, uses no YAML aliases or Python
tags, emits ASCII-safe UTF-8, and ends with exactly one newline. Rendering the same summary twice
must produce identical bytes.

- [ ] **Step 3: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_coverage.py tests/unit/reference_catalog/test_rendering.py -q`

- [ ] **Step 4: Implement derived coverage only**

```python
def calculate_coverage(
    records: Sequence[UpstreamLedgerRecord],
    *,
    source_order: Sequence[str],
) -> CoverageSummary: ...


def render_coverage_yaml(summary: CoverageSummary) -> bytes: ...
```

Use `Counter` over enum values, then materialize every enum key including zero counts. Do not scan
checkouts, open source files, or embed 1464 as a generator constant. Promptfoo summary derives from
`source_asset_kind`; SABER split derives from `scenario_class` and must match the approved
`expected_upstream_total=716` invariant already enforced by `SaberDiscoverer`. PyYAML uses `safe_dump`,
`sort_keys=False`, stable indentation, no aliases, and one terminal newline.

- [ ] **Step 5: Verify GREEN and conservation failure paths**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_coverage.py tests/unit/reference_catalog/test_rendering.py -q
.venv/bin/mypy src/agentsec_eval/reference_catalog/coverage.py src/agentsec_eval/reference_catalog/rendering.py tests/unit/reference_catalog/test_coverage.py tests/unit/reference_catalog/test_rendering.py
```

- [ ] **Step 6: Commit**

```bash
git add src/agentsec_eval/reference_catalog/coverage.py src/agentsec_eval/reference_catalog/rendering.py tests/unit/reference_catalog/test_coverage.py tests/unit/reference_catalog/test_rendering.py
git commit -m "catalog: render and validate coverage ledger"
```

### Task 9: Add one generation pipeline and generate/check CLI

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Create: `src/agentsec_eval/reference_catalog/generation.py`
- Create: `src/agentsec_eval/reference_catalog/cli.py`
- Create: `tests/unit/reference_catalog/test_generation.py`
- Modify: `src/agentsec_eval/reference_catalog/__init__.py`
- Modify: `src/agentsec_eval/reference_catalog/discovery/__init__.py`

**Interfaces:**
- Consumes: repository root, catalog locks, ordered discoverers, and committed output paths.
- Produces: one in-memory `GeneratedCatalog`, transactional `generate`, read-only `check`, and
  stable CLI exit codes.

- [ ] **Step 1: Write failing orchestration tests**

Inject fake lock verification and discoverers. Assert order is lock order; all records are combined
before validation; JSONL and coverage receive the same tuple; any lock/discovery/validation/render
failure leaves both old outputs byte-identical; and a duplicate identity fails before writing.

- [ ] **Step 2: Write failing CLI tests**

Call `main([...])` directly. Assert only `generate` and `check` subcommands exist, `generate` writes
the pair once, `check` returns 0 for exact bytes and nonzero for missing/drifted output, and `check`
never changes file content or mtime. Errors go to stderr without source payloads.

- [ ] **Step 3: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_generation.py -q`

- [ ] **Step 4: Implement the ordered discoverer factory**

```python
def catalog_discoverers() -> tuple[SourceDiscoverer, ...]:
    return (
        SaberDiscoverer(),
        CodeIPIDiscoverer(),
        TerminalBenchDiscoverer(),
        MCPSafetyBenchDiscoverer(),
        MCPSecBenchDiscoverer(),
        PromptfooDiscoverer(),
        *reference_discoverers(),
    )
```

No central `if source_project == ...` dispatch is allowed. Every source-specific decision remains
inside its discoverer.

- [ ] **Step 5: Implement in-memory generation and drift checking**

```python
@dataclass(frozen=True)
class CatalogPaths:
    repository_root: Path
    ledger_path: Path
    coverage_path: Path


@dataclass(frozen=True)
class GeneratedCatalog:
    records: tuple[UpstreamLedgerRecord, ...]
    coverage: CoverageSummary
    rendered: RenderedCatalog


def build_catalog(paths: CatalogPaths) -> GeneratedCatalog: ...
def generate_catalog(paths: CatalogPaths) -> GeneratedCatalog: ...
def check_catalog(paths: CatalogPaths) -> GeneratedCatalog: ...


class CatalogDriftError(RuntimeError):
    pass
```

`build_catalog` performs exactly: load locks -> verify every checkout -> invoke discoverers ->
validate all records -> calculate coverage -> render both outputs in memory. `generate_catalog`
calls `replace_outputs_transactionally` only after `build_catalog` succeeds. `check_catalog`
compares bytes and raises `CatalogDriftError` with path plus digest, never output contents.

- [ ] **Step 6: Add one command with exactly two subcommands**

```toml
[project.scripts]
agentsec-reference-catalog = "agentsec_eval.reference_catalog.cli:main"
```

`main(argv: Sequence[str] | None = None) -> int` uses `argparse`; both subcommands accept only
`--repository-root` (default `.`). Output paths are fixed under `references/upstream-index/` and
cannot be redirected into a second dataset.

- [ ] **Step 7: Add hermetic CI for catalog tooling**

Update the existing `quality` install to `pip install -e ".[dev,catalog]"`, exclude
`reference_catalog` alongside Docker tests in its ordinary Pytest marker expression, and add a
focused command for `tests/unit/reference_catalog`. That unmarked unit directory includes Task 10's
`test_committed_outputs.py`, so Hosted CI validates committed JSONL/Coverage bytes without cloning
upstream projects. Register:

```toml
markers = [
  # existing markers
  "reference_catalog: requires complete locked upstream reference checkouts",
]
```

Hosted CI does not clone upstream projects. It validates committed artifacts from repository files;
source reconciliation and `check_catalog()` full rescans remain explicit integration gates in the
prepared workspace.

- [ ] **Step 8: Verify GREEN**

Run:

```bash
.venv/bin/pip install -e ".[dev,catalog]"
.venv/bin/pytest tests/unit/reference_catalog -q
.venv/bin/ruff check src/agentsec_eval/reference_catalog tests/unit/reference_catalog
.venv/bin/mypy src/agentsec_eval/reference_catalog tests/unit/reference_catalog
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml src/agentsec_eval/reference_catalog tests/unit/reference_catalog
git commit -m "catalog: add deterministic generate and check commands"
```

### Task 10: Reconcile full checkouts and generate the committed ledger

**Files:**
- Create: `tests/unit/reference_catalog/test_committed_outputs.py`
- Create: `tests/integration/reference_catalog/conftest.py`
- Create: `tests/integration/reference_catalog/test_locked_source_reconciliation.py`
- Create: `tests/integration/reference_catalog/test_committed_catalog.py`
- Create: `references/upstream-index/ac-upstream-asset-index.jsonl`
- Create: `references/upstream-index/ac-upstream-coverage.yaml`

**Interfaces:**
- Consumes: committed outputs in a Hosted-CI-safe unit test, plus every complete locked checkout in
  separately marked integration tests.
- Produces: the reviewed 1464-row safe metadata ledger, byte-consistent derived coverage, Hermetic
  committed-pair validation, and source reconciliation evidence.

- [ ] **Step 1: Add the unmarked Hermetic committed-output test**

`tests/unit/reference_catalog/test_committed_outputs.py` reads only:

```text
references/upstream-index/ac-upstream-asset-index.jsonl
references/upstream-index/ac-upstream-coverage.yaml
```

It must not import/call `build_catalog` or `check_catalog`, load source locks, access a checkout, or
carry the `reference_catalog` marker. Parse every non-empty line with
`UpstreamLedgerRecord.model_validate_json`, then call `validate_records`. Derive `source_order` from
first occurrence in the validated JSONL tuple, call `calculate_coverage(records, source_order=...)`,
and compare `render_coverage_yaml(summary)` byte-for-byte with the committed YAML.

The test also asserts exactly 1464 lines, global identity uniqueness, role conservation
`1017+89+6+291+38+8+15=1464`, native conversion conservation
`1106+174+10+169+3+2=1464`, null initial native outputs, no Adapter Candidate selector kinds, no
prohibited raw-content fields, and no host absolute paths. Source repository URLs and
repository-relative provenance paths remain allowed.

```python
def test_committed_outputs_are_valid_and_self_consistent(repository_root: Path) -> None:
    ledger_path = repository_root / "references/upstream-index/ac-upstream-asset-index.jsonl"
    coverage_path = repository_root / "references/upstream-index/ac-upstream-coverage.yaml"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    records = validate_records(tuple(UpstreamLedgerRecord.model_validate_json(line) for line in lines))
    assert len(records) == 1464
    source_order = tuple(dict.fromkeys(record.source_project for record in records))
    summary = calculate_coverage(records, source_order=source_order)
    assert render_coverage_yaml(summary) == coverage_path.read_bytes()
```

- [ ] **Step 2: Add explicitly marked full-checkout tests**

At module scope:

```python
pytestmark = [pytest.mark.integration, pytest.mark.reference_catalog]
```

Both integration modules carry those markers. `conftest.py` derives the repository root from
`__file__`, calls `load_catalog_locks`, and verifies all checkouts. It contains no `/root/...`
literal. Explicit invocation fails, rather than skips, if a checkout is missing or wrong; ordinary
unit/Hosted-CI commands exclude the marker.

- [ ] **Step 3: Add exact source reconciliation assertions**

`test_locked_source_reconciliation.py` calls each discoverer independently and asserts:

```python
EXPECTED_SOURCE_COUNTS = {
    "saber": 716,
    "inspect-evals-codeipi": 45,
    "terminal-bench-2": 89,
    "mcp-safetybench": 245,
    "mcpsecbench": 17,
    "promptfoo": 329,
    "harbor": 8,
    "mcp-universe": 15,
}
```

Also assert SABER 289/186/241, MCPSecBench 11 structured plus 6 taxonomy, Promptfoo 155 concrete
Plugins, 16 Collections, 120 alias-only selectors, 37 accepted Strategies, one registry-only stub,
13 Coding Agent Plugins, six IDs in the source-declared `MCP_PLUGINS` set, 91 remote-only concrete
Plugins, 10 dataset-backed concrete Plugins, 22 target-independent Strategy IDs, 15
target-feedback Strategy IDs, and four cross-Run Strategy IDs. Freshly recompute every record
digest from its locked source unit.

- [ ] **Step 4: Add the full-rescan committed-catalog integration test**

`tests/integration/reference_catalog/test_committed_catalog.py` calls `check_catalog()` and asserts
the committed pair matches a fresh full-checkout scan. It owns source drift, lock, digest, Promptfoo
Registry, and SABER reconciliation evidence only. It does not duplicate the Hermetic per-line,
conservation, forbidden-field, or Coverage byte-recalculation assertions.

- [ ] **Step 5: Verify both RED paths before generation**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_committed_outputs.py -q
.venv/bin/pytest -m reference_catalog tests/integration/reference_catalog -q
```

Expected: the Hermetic test and `check_catalog()` integration test fail because the JSONL and
Coverage files do not exist; source reconciliation tests must already pass. If source reconciliation
fails, stop and report concrete missing/extra IDs before generating anything.

- [ ] **Step 6: Generate once, verify twice, and run both test layers**

Run:

```bash
.venv/bin/agentsec-reference-catalog generate --repository-root .
.venv/bin/agentsec-reference-catalog check --repository-root .
.venv/bin/agentsec-reference-catalog check --repository-root .
.venv/bin/pytest tests/unit/reference_catalog/test_committed_outputs.py -q
.venv/bin/pytest -m reference_catalog tests/integration/reference_catalog -q
wc -l references/upstream-index/ac-upstream-asset-index.jsonl
git diff --check
```

Expected: both checks return 0 without modifying files; the Hosted-CI-safe artifact test and
full-checkout integration tests pass; `wc -l` reports 1464; the diff contains only safe metadata
outputs and tests.

- [ ] **Step 7: Run explicit leak and duplicate scans**

Run:

```bash
! rg -n '"(prompt|payload|fixture|solution|credential|service_url|implementation_code|evaluator_label)"\s*:' references/upstream-index/ac-upstream-asset-index.jsonl
! rg -n '/root/|/home/|file://' references/upstream-index
.venv/bin/python -c 'import json; from pathlib import Path; rows=[json.loads(line) for line in Path("references/upstream-index/ac-upstream-asset-index.jsonl").read_text(encoding="utf-8").splitlines()]; keys=[(r["source_project"],r["source_path"],r["source_record_key"]) for r in rows]; assert len(rows)==1464==len(set(keys))'
```

- [ ] **Step 8: Commit generated metadata and its Hermetic verifier together**

```bash
git add tests/unit/reference_catalog/test_committed_outputs.py tests/integration/reference_catalog references/upstream-index
git commit -m "references: generate full A/C upstream ledger"
```

### Task 11: Rename the 18-record validation selection and update terminology

**Files:**
- Rename: `references/import-selection/ac-seed-selection.yaml` ->
  `references/validation-selection/ac-conversion-validation.yaml`
- Modify: `docs/development/ac-asset-ingestion-spike.md`
- Modify: `docs/superpowers/specs/2026-07-17-ac-full-asset-catalog-design.md`
- Modify: `tests/unit/reference_catalog/test_validation.py`

**Interfaces:**
- Consumes: the existing 18 provenance-locked validation records and committed ledger identities.
- Produces: one conversion-validation selection, no copied scenario data, and no stale import/seed
  terminology.

- [ ] **Step 1: Add failing structured selection tests**

Load the YAML with `yaml.safe_load` and recursively count mappings containing `source_locator`.
Assert exactly 18, every locator identity exists in the JSONL ledger, each digest matches that row,
no scenario content is duplicated from the ledger or source, and smoke execution IDs are native
Scenario Asset IDs only when non-null.

Add local typed test helpers `load_yaml(path)`, `collect_mappings_with_key(value, key)`,
`locator_identity(locator)`, and `ledger_identities(repository_root)`. They parse structured data,
return immutable tuples/sets, and never use text matching to establish membership.

```python
def test_conversion_validation_records_are_ledger_subset(
    repository_root: Path,
) -> None:
    selection = load_yaml(
        repository_root / "references/validation-selection/ac-conversion-validation.yaml"
    )
    records = collect_mappings_with_key(selection, "source_locator")
    assert len(records) == 18
    assert {locator_identity(item["source_locator"]) for item in records} <= ledger_identities(
        repository_root
    )
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/reference_catalog/test_validation.py -q`

Expected: the new validation-selection path does not exist.

- [ ] **Step 3: Rename without copying and update precise terms**

Use `git mv`. Rename the top-level `selection_version` key to
`conversion_validation_version` and set `status: conversion_validation_only`; preserve the 18
records' approved semantic corrections, authorization contexts, assertion applicability, and
source locators. Update A/C docs to use `conversion validation records`, `schema validation
records`, and `smoke execution IDs`. Convert the design's future-tense move statement to the final
path. This implementation plan may retain the old path only inside the explicit rename instruction.

- [ ] **Step 4: Verify GREEN and absence of stale dataset language**

Run:

```bash
.venv/bin/pytest tests/unit/reference_catalog/test_validation.py -q
! rg -n 'references/import-selection/ac-seed-selection.yaml|seed selection|fixed input set|selected candidates' docs/development/ac-asset-ingestion-spike.md docs/superpowers/specs/2026-07-17-ac-full-asset-catalog-design.md references/validation-selection/ac-conversion-validation.yaml
test ! -e references/import-selection/ac-seed-selection.yaml
test ! -d references/import-selection
```

Expected: exactly 18 structured records remain, all are ledger members, and no second dataset or
scenario copy exists.

- [ ] **Step 5: Commit terminology and rename separately**

```bash
git add docs/superpowers/specs/2026-07-17-ac-full-asset-catalog-design.md docs/development/ac-asset-ingestion-spike.md references/validation-selection tests/unit/reference_catalog/test_validation.py
git add -u references/import-selection
git commit -m "docs: finalize validation selection terminology"
```

### Task 12: Run the complete matrix and open a Draft PR

**Files:**
- Modify only if evidence exposes a defect: files owned by the failing prior task.
- Do not add native scenarios, adapters, a second generator, or unplanned cleanup.

**Interfaces:**
- Consumes: all prior commits and prepared full checkouts.
- Produces: one Draft PR with complete local evidence and a clean branch.

- [ ] **Step 1: Run catalog-specific tests and two drift checks**

```bash
.venv/bin/pytest tests/unit/reference_catalog -q
.venv/bin/pytest -m reference_catalog tests/integration/reference_catalog -q
.venv/bin/agentsec-reference-catalog check --repository-root .
.venv/bin/agentsec-reference-catalog check --repository-root .
```

- [ ] **Step 2: Run the repository quality matrix**

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -m "not docker and not reference_catalog" --ignore=tests/unit/integrations/pyrit --ignore=tests/integration/m0b
.venv/bin/mypy src/agentsec_eval/integrations/pyrit/__init__.py src/agentsec_eval/integrations/pyrit/scorer.py tests/unit/integrations/pyrit/test_scorer.py tests/integration/m0b/test_pyrit_scorer.py
.venv/bin/pytest tests/unit/integrations/pyrit tests/integration/m0b tests/unit/integrations/test_pyrit_import_boundary.py
git diff --check
```

Run Docker-marked M0-A tests when Docker is available, matching the existing CI gate:

```bash
.venv/bin/pytest -m docker tests/integration/m0a
```

- [ ] **Step 3: Reconfirm acceptance counts from structured outputs**

Use Python JSON/YAML parsing, not text grep, to assert all 15 acceptance gates below. Save command
output in the Draft PR body; do not commit host paths, timestamps, or transient logs.

- [ ] **Step 4: Confirm commit and worktree boundaries**

```bash
git log --oneline 5731102d773a6f52dadea2bd1f94e552ab2f8caa..HEAD
git status --short
git diff --check 5731102d773a6f52dadea2bd1f94e552ab2f8caa..HEAD
```

Expected: the planned reviewable commits are visible and the worktree is clean.

- [ ] **Step 5: Push and open a Draft PR**

```bash
git push origin codex/ac-full-asset-catalog
gh pr create --draft --base main --head codex/ac-full-asset-catalog --title "catalog: build full A/C upstream ledger" --body-file /tmp/ac-full-asset-catalog-pr.md
```

The PR body reports exact counts, parser pins, source-only/no-execution evidence, unit/full-checkout
test split, deterministic check results, license/conversion separation, and remaining native-asset
non-goals.

## Planned Commits

The implementation expands the suggested source commit into reviewable source-family commits:

1. `catalog: define upstream ledger models and invariants`
2. `catalog: add deterministic digest and lock verification`
3. `catalog: discover and reconcile SABER records`
4. `catalog: discover CodeIPI and Terminal-Bench records`
5. `catalog: discover MCP benchmark and taxonomy records`
6. `catalog: discover Promptfoo source entries`
7. `catalog: index implementation and source references`
8. `catalog: render and validate coverage ledger`
9. `catalog: add deterministic generate and check commands`
10. `references: generate full A/C upstream ledger`
11. `docs: finalize validation selection terminology`

Commit 6 includes `promptfoo_policy.py` and its independent policy tests. Commit 10 includes the two
generated outputs and unmarked `test_committed_outputs.py`, so policy coverage and committed-pair
consistency land with the artifacts they protect.

## Acceptance Gates

1. `check` runs twice with exit 0 and no file or mtime changes.
2. JSONL contains exactly 1464 lines.
3. Role counts satisfy `1017+89+6+291+38+8+15=1464`.
4. Native conversion counts satisfy `1106+174+10+169+3+2=1464`.
5. SABER contains 716 records split A/B/C as 289/186/241.
6. Promptfoo contains 155 concrete Plugins, 16 Collections, 120 alias-only selectors, 37 accepted
   Strategies, and one registry-only stub.
7. No Collection, alias, preset, or stub is a concrete Adapter Candidate.
8. No restricted upstream prose, payload, fixture, solution, credential, service URL, evaluator
   label, or implementation code is copied.
9. The generator executes no upstream code.
10. No second dataset or Scenario Asset copy exists.
11. Ordinary unit tests use no host absolute path or full checkout, and Hosted CI's unmarked
    committed-output test recalculates Coverage from JSONL and proves byte equality with YAML.
12. Full-checkout tests remain explicitly marked and independently executable for locks, source
    counts, digests, Registry/Manifest reconciliation, and `check_catalog()` rescans.
13. Ruff, format, strict MyPy, ordinary Pytest, full-checkout catalog tests, PyRIT tests, and the
    available Docker gate pass.
14. `git diff --check` passes.
15. The final worktree is clean and the pushed remote branch matches local HEAD.

## Stop Conditions

Stop before writing outputs or advancing to the next task if:

- a lock is missing, dirty, shallow, partial, at the wrong commit, or has a different remote;
- source discovery yields a missing/extra/duplicate identity or a shape not covered by the approved
  parser/record contract;
- a parser change would require executing TypeScript or broadening beyond approved source nodes;
- any count or conservation equation fails;
- a safe digest cannot be computed without storing restricted content;
- transactional replacement cannot restore the previous committed pair on a handled Python-level
  failure; or
- implementation requires changing the approved macro design.

Report the concrete source, path, record key, expected/observed count, or unsupported AST node. Do
not hide an enumeration failure as `malformed` or relax an invariant to continue.

## Dry-Run Findings

- SABER's `tasks/` tree also contains `pilot_tasks.json`; the approved glob must be
  `tasks/{A,B,C}/{category}/*.json`, otherwise discovery would incorrectly observe 717 JSON files.
- MCPSecBench's 17 taxonomy headings use four spelling variants relative to its 11 structured
  records. The explicit alias table is required to derive six taxonomy-only rows deterministically.
- The mutable `reference-sources/promptfoo` checkout is not the locked source; the manifest locator
  must point to the clean `promptfoo-locked-fcde2e89` checkout.
- Two fixed output paths cannot form one portable operating-system transaction. The plan uses
  transactional two-file replacement with staged writes, Python-level rollback, and committed-pair
  consistency validation. Each `os.replace` is atomic; a crash or power loss between replacements
  is not automatically rolled back.
- Hosted CI does not contain upstream checkouts. Its unmarked Hermetic Artifact Test strictly parses
  committed JSONL, recalculates Coverage, and compares YAML bytes; the explicitly marked integration
  gate separately verifies locked sources and full rescans in the prepared workspace.
- Promptfoo's Registry imports runtime/strategy modules that need not exist for metadata extraction.
  Registry ID mode must ignore those imports and opaque action subtrees, while Static Constant
  Module mode retains strict four-module import resolution.

## Final Validation

Completion requires all commands in Task 12 plus structured proof of every acceptance count, Hosted
Hermetic committed-pair validation, full-checkout reconciliation, two clean `check` executions, one
safe-content scan, a clean worktree, a pushed branch, and a Draft PR. Test success alone does not
authorize generation of native Scenario Assets or Promptfoo Adapters.

## First Execution Step

After this plan is approved, start Task 1 by writing the failing model and role/output invariant
tests. Do not begin with a discoverer or generated file.
