# A/C Full Asset Catalog Design

- Status: approved for specification review
- Date: 2026-07-17
- Baseline: `main@946d2cd7fc1f3819397b491e0bb174a4029696f3`
- Branch: `codex/ac-full-asset-catalog`
- Scope: documentation and safe upstream metadata only; no runtime code or native scenario generation

## Purpose

This change corrects the earlier implication that 18 Spike candidates define the A/C dataset. The
project has one canonical native scenario asset collection. The 18 existing records are only
conversion and schema validation inputs. They neither set the collection boundary nor form a
second, smaller dataset.

The change must exhaustively enumerate the locked upstream A/C asset surfaces, reconcile their
counts, and document how future semantic conversion produces the one canonical collection. It
must not copy restricted task text, prompts, payloads, fixture contents, solutions, credentials,
service URLs, evaluator labels, or implementation code.

The governing set relationship is:

```text
Validation records ⊂ Canonical full asset catalog
```

Validation records contain identifiers and conversion expectations only. Smoke, regression, and
debug execution select canonical assets by native ID, tag, or filter and never copy scenario
content.

## Approaches Considered

### A. Record-level exhaustive index

Create one JSONL line for every real upstream task, embedded sample, task directory, structured
attack record, or declared taxonomy-only attack asset in the locked discovery surfaces. Index the
already audited Harbor and MCP-Universe implementation/source references separately without
calling them scenarios.

- Advantages: preserves the upstream unit of identity, proves complete discovery, supports
  one-to-one conversion accounting, and does not inflate counts with support files.
- Cost: each source family needs an explicit discovery and digest rule.
- Decision: adopt this approach.

### B. File-level exhaustive index

Index every file under the relevant upstream directories.

- Advantage: mechanically simple traversal.
- Rejected because: orchestration YAML, scripts, fixtures, solutions, experiment rows, and task
  records would become indistinguishable. Counts would describe repository layout rather than
  scenario assets and could mislabel framework source as data.

### C. Concept or taxonomy index

Index only representative categories and attack concepts.

- Advantage: small review surface.
- Rejected because: it collapses hundreds of distinct upstream records, repeats the original
  sampling error, and cannot prove discovery or conversion count conservation.

## One Asset Flow

There is exactly one ingestion flow:

```text
Locked Upstream Sources
  -> Full Discovery
  -> Full Upstream Asset Index
  -> Semantic Conversion
  -> Canonical Native Scenario Assets
  -> Evaluation-Time Selection
```

`references/upstream-index/ac-upstream-asset-index.jsonl` is a safe metadata ledger, not a native
dataset. `references/validation-selection/ac-conversion-validation.yaml` identifies records used to
exercise importer and schema behavior, not a sample dataset. Future native assets have exactly one
root and identity boundary:

```text
assets/scenarios/{native_asset_id}/
```

This task documents that boundary but does not create `assets/scenarios/` or assign native asset
IDs. Every index line therefore has `native_asset_id: null`.

Formal evaluation defaults to:

```text
all assets where status=validated and eval_eligible=true
```

CI, smoke, regression, and debugging may select a subset only by referencing native IDs, tags, or
filters over the same canonical collection. No selection may duplicate scenario content.

## Discovery Boundaries and Expected Counts

All checkouts are read-only inputs. Before discovery, each checkout must exist, be clean, and match
the repository and commit in `references/source-locks/ac-reference-sources.yaml`.

| Source | Discovery unit | Count | Index role |
|---|---|---:|---|
| SABER | Every JSON task represented by `dataset/manifest.json` and present under `tasks/` | 716 | Upstream A-class task records |
| Inspect Evals / CodeIPI | Every embedded record in `src/inspect_evals/ipi_coding_agent/dataset/samples.json` | 45 | Upstream A-class task records |
| Terminal-Bench 2 | Every top-level task directory at the locked commit | 89 | Upstream A-class task records |
| MCP-SafetyBench | Every JSON attack task under `mcpuniverse/benchmark/configs/test/*/*.json` | 245 | Upstream C-class task records |
| MCPSecBench | 11 structured `data/data.json` records plus 6 taxonomy-only declared attack categories | 17 | Upstream C-class attack assets |
| Harbor | The 8 files already named in the source lock's `audited_files` | 8 | Implementation references only |
| MCP-Universe | The 15 files already named in the source lock's `audited_files` | 15 | Source and implementation references only |
| **Total** |  | **1135** |  |

MCP-SafetyBench dataset YAML files are orchestration manifests and do not become additional task
records. Supporting source files do not become task records. Harbor and MCP-Universe are indexed
only in their established reference roles; their framework files must never be represented as
scenario data.

SABER has a stronger reconciliation gate. Its manifest must contain 716 unique task IDs, the task
tree must contain 716 parseable JSON records, and the two ID sets must have no missing, extra, or
duplicate IDs. The expected scenario split is A=289, B=186, and C=241. Any mismatch fails generation
and reports the concrete IDs.

## Index Contract

`references/upstream-index/ac-upstream-asset-index.jsonl` contains one JSON object per discovery
unit. Every object contains all of these fields:

```json
{
  "source_project": "",
  "source_repository": "",
  "source_commit": "",
  "source_path": "",
  "source_record_key": "",
  "source_record_digest": "",
  "asset_family": "",
  "scenario_class": "",
  "category": "",
  "attack_present": null,
  "attack_origin": null,
  "attack_delivery_mode": null,
  "conversion_status": "",
  "conversion_reason": "",
  "license_disposition": "",
  "native_asset_id": null
}
```

Paths are repository-relative POSIX paths. Digests are lowercase 64-character SHA-256 hex values.
The three attack fields are populated only when the upstream metadata supports the claim; absence
or ambiguity remains JSON `null`. Reference-only rows use `scenario_class: "reference_only"` and
an `asset_family` that explicitly names `implementation_reference` or `source_reference`.

Lines are deterministic: source projects follow source-lock order, then records sort by
`source_path` and `source_record_key`. JSON uses UTF-8, sorted keys, compact separators, and one
trailing newline per object. The index includes no host absolute path or scan timestamp.

`conversion_status` is one of the mutually exclusive coverage dispositions:

- `convertible`
- `blocked_by_license`
- `unsupported`
- `duplicate`
- `intentionally_excluded`
- `malformed`
- `conversion_failed`

`conversion_reason` states the concrete reason for the disposition. `license_disposition` records
the applicable source-lock decision independently from conversion status. No row in this task is a
completed native conversion.

## Digest Rules

Digesting identifies the discovered unit without copying its content:

- SABER JSON tasks: SHA-256 of canonical JSON using sorted keys, compact separators, and UTF-8.
- CodeIPI embedded records: the same canonical JSON digest, one digest per array record.
- MCP-SafetyBench JSON tasks: the same canonical JSON digest, one digest per task file.
- Terminal-Bench 2 task directories: recursively enumerate every regular file in repository-relative
  POSIX order, compute each raw file SHA-256, serialize each entry as `path:file_sha256\n`, and hash
  the concatenated UTF-8 manifest. Symlinks, unreadable entries, and path escape fail closed.
- MCPSecBench structured records: the canonical JSON digest of each record.
- MCPSecBench taxonomy-only assets: SHA-256 of the normalized source path, record key, and declared
  category joined with newline characters.
- Harbor and MCP-Universe references: raw file SHA-256.

Source scripts, Dockerfiles, setup commands, evaluators, and cleanup code are never executed while
discovering or digesting.

## Coverage and Conservation

`references/upstream-index/ac-upstream-coverage.yaml` is derived from the same in-memory record list
as the JSONL index. It is not maintained as an independent manual count. Every project records:

```yaml
source_project:
  discovered_total:
  indexed_total:
  convertible:
  blocked_by_license:
  unsupported:
  duplicate:
  intentionally_excluded:
  malformed:
  conversion_failed:
```

Two invariants apply to every project:

```text
indexed_total = discovered_total

discovered_total
= convertible
+ blocked_by_license
+ unsupported
+ duplicate
+ intentionally_excluded
+ malformed
+ conversion_failed
```

The initial conservative dispositions are:

| Source | blocked_by_license | unsupported | intentionally_excluded |
|---|---:|---:|---:|
| SABER | 716 | 0 | 0 |
| Inspect Evals / CodeIPI | 45 | 0 | 0 |
| Terminal-Bench 2 | 89 | 0 | 0 |
| MCP-SafetyBench | 245 | 0 | 0 |
| MCPSecBench | 11 | 6 | 0 |
| Harbor | 0 | 0 | 8 |
| MCP-Universe | 0 | 0 | 15 |

All unlisted dispositions are zero. The 11 structured MCPSecBench records remain license-blocked;
the 6 taxonomy-only categories are unsupported as record-level conversion inputs. Harbor and
MCP-Universe references are intentionally excluded from scenario conversion because their role is
implementation/source evidence. License review may change future conversion eligibility but must
not change discovery totals for the locked commits.

The SABER coverage entry additionally records `expected_upstream_total: 716`. Generation fails if
its discovered or indexed total differs from 716.

## Validation Selection Semantics

`references/import-selection/ac-seed-selection.yaml` moves to
`references/validation-selection/ac-conversion-validation.yaml`. Its 18 records remain provenance-
locked conversion and schema validation records. Existing semantic corrections, authorization
contexts, assertion applicability, and reconstruction constraints remain intact.

The file and Spike documentation replace dataset-like terms such as `seed selection`, `fixed input
set`, and `selected candidates` with the precise terms `conversion validation records`, `schema
validation records`, and `smoke execution IDs`. A validation record may point to an upstream index
record and a proposed conversion shape, but it may not embed a second copy of a canonical scenario.
Smoke execution IDs are native asset IDs only and become usable only after those native assets
exist.

## Failure Handling

Discovery and index generation fail before replacing committed output when any of these occurs:

- a checkout is absent, dirty, detached from the locked commit, or has a different remote identity;
- a path is absolute, escapes its checkout, is unreadable, or violates the source-specific shape;
- SABER manifest and task IDs differ, repeat, or do not total 716;
- the same source-project/path/record-key identity is emitted twice without a `duplicate`
  disposition;
- a required digest is not a valid SHA-256 value;
- any required JSONL field is absent or has the wrong type;
- `indexed_total` differs from `discovered_total`;
- a project's conservation equation fails; or
- the aggregate index count differs from 1135 for these locked commits.

A source record that is itself malformed or unsupported can still be indexed safely with that
disposition when its path, key, and digest are determinable. An enumeration failure that prevents
the record from being counted is fatal and cannot be hidden in `malformed`.

## Verification

Verification uses structured JSON/YAML parsing and checks:

1. The JSONL has exactly 1135 parseable objects and every object has exactly the required fields.
2. Each source count matches the discovery table and every row matches the locked repository and
   commit.
3. SABER has 716 unique reconciled IDs with the A/B/C split 289/186/241.
4. Every digest matches a fresh read-only scan of the locked checkout.
5. Every project satisfies both coverage invariants and the coverage totals equal the JSONL totals.
6. All `native_asset_id` values are null and no `assets/scenarios/` content is created.
7. The renamed validation file still has exactly 18 validation records and contains no claim that
   those records define dataset scope.
8. Repository search finds no remaining references to the removed import-selection path or the
   prohibited dataset-like terminology in the changed A/C documents.
9. The diff touches only documentation and reference metadata; runtime code remains unchanged.
10. Existing Ruff, formatting, MyPy, non-Docker tests, and PyRIT checks continue to pass.

The final worktree must be clean after commits. The branch is pushed to the existing GitHub remote
and opened as a separate Draft PR because this change defines the catalog and ingestion contract;
it does not claim that canonical native Scenario Packs have been generated.
