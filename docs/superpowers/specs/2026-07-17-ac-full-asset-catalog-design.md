# A/C Full Upstream Ledger and Native Asset Catalog Design

- Status: approved for implementation planning
- Date: 2026-07-17
- Baseline: `main@946d2cd7fc1f3819397b491e0bb174a4029696f3`
- Branch: `codex/ac-full-asset-catalog`
- Scope: documentation and safe upstream metadata only; no runtime code, implementation plan,
  upstream index, or native scenario generation

## Purpose

This change corrects the earlier implication that 18 Spike candidates define the A/C dataset. The
project has one canonical native scenario asset collection. The 18 existing records are only
conversion and schema validation inputs. They neither set the collection boundary nor form a
second, smaller dataset.

The change must exhaustively enumerate the locked upstream A/C benchmark, normal-task fixture,
attack-taxonomy, Promptfoo generator/delivery, and implementation/source-reference surfaces. It
must reconcile their counts without calling every ledger row a scenario. It must not copy
restricted task text, prompts, payloads, fixture contents, solutions, credentials, service URLs,
evaluator labels, or implementation code.

The two set relationships are:

```text
Conversion-validation source records
⊂ Full upstream ledger

Native outputs derived from validation records
⊂ Canonical native scenario collection
```

The 18 conversion-validation records select upstream ledger entries for conversion and schema
validation. They are not a second dataset and are not native assets that have not yet been
generated. Smoke, regression, and debug execution select canonical assets by native ID, tag, or
filter and never copy scenario content.

## Promptfoo Version Decision

`references/manifest.yaml` locks Promptfoo to:

```text
repository: https://github.com/promptfoo/promptfoo
commit: fcde2e89a89dc4ca79dcc3012927f50193251759
package version: 0.121.19
role: attack candidate generator
```

The local repository is a complete clone: it is neither shallow nor partial and contains the
locked commit. A detached read-only checkout of that commit was scanned. The source contains the
planned Coding Agent and MCP plugins, Plugin collections and aliases, static and adaptive Strategy
registries, and Meta, Hydra, and Goblin providers. No version relock is required before catalog
implementation. Git describes the fixed commit as `0.121.19-2-gfcde2e89a`; the commit is the lock,
not the release tag or mutable package version.

The locked source, not the online documentation, is authoritative. Its registry contains:

- 155 concrete Plugin IDs;
- 16 Plugin Collection IDs;
- 121 alias selector IDs, with `bias` also present as a Collection, producing 291 unique accepted
  Plugin selectors;
- 13 concrete Coding Agent Plugin IDs;
- 6 IDs in the source-declared `MCP_PLUGINS` set;
- 91 concrete Plugin IDs marked remote-only by the locked source;
- 10 concrete dataset-backed Plugin IDs;
- 37 accepted Strategy IDs;
- one additional registry-only deprecated `simba` no-op, producing 38 Strategy ledger records;
- one Strategy collection, `other-encodings`, which expands to `camelcase`, `morse`, `piglatin`, and
  `emoji`; and
- two accepted Plugin aliases, `nist:ai` and `personal-safety`, with no expansion mapping at this
  commit. They remain visible and are classified `unsupported`; they are not silently dropped.

The Strategy source also exposes three accepted IDs that are not concrete registry entries:
`default` is a preset, `other-encodings` is a collection, and deprecated `multilingual` is handled
outside the main Strategy registry. Conversely, `simba` remains in the registry but is absent from
the accepted Strategy constant and returns no cases. The ledger records these distinctions through
`source_asset_kind`.

The source-declared MCP Plugin set count is 6. It is not the project's final MCP-applicability
count: other entries such as indirect prompt injection, excessive agency, or tool discovery may be
classified `mcp_applicable: true` during ledger generation. That broader count is derived from the
completed ledger and must not be inferred from `MCP_PLUGINS` alone.

## Approaches Considered

### A. One role-aware record ledger

Create one JSONL line for every upstream benchmark record, normal task fixture, taxonomy record,
accepted Promptfoo Plugin selector, accepted Promptfoo Strategy identifier, registry-only Strategy
stub, or locked implementation/source reference. Preserve the upstream unit of identity and assign
every line an explicit role and source kind.

- Advantages: proves full discovery, keeps one ledger, distinguishes scenarios from capabilities
  and references, and supports one-to-one conversion accounting.
- Cost: every source family needs an explicit discovery, digest, role, and conversion rule.
- Decision: adopt this approach.

### B. File-level exhaustive index

Index every file under the relevant upstream directories.

- Advantage: mechanically simple traversal.
- Rejected because: orchestration YAML, scripts, fixtures, solutions, experiment rows, task records,
  and implementation files would become indistinguishable. Counts would describe repository layout
  rather than source assets.

### C. Benchmark-only or concept-only index

Index only benchmark records or representative attack concepts.

- Advantage: smaller review surface.
- Rejected because: it omits the already approved Promptfoo candidate-generation role, collapses
  distinct upstream records, repeats the original sampling error, and cannot prove discovery or
  conversion count conservation.

## One Ledger and Typed Native Outputs

There is exactly one upstream ledger and one canonical native scenario collection, with typed
downstream flow:

```text
Locked Upstream Sources
  -> Full Discovery
  -> Full Upstream Ledger
       |-- benchmark scenarios / normal-task fixtures / attack taxonomies
       |     `-- semantic conversion -> assets/scenarios/
       |-- Promptfoo generation and strategy entries
       |     `-- capability adaptation -> project generator/policy adapter registry
       `-- selectors and implementation/source references
             `-- no native runtime output
```

`references/upstream-index/ac-upstream-asset-index.jsonl` is one safe upstream metadata ledger, not
a native dataset. `references/validation-selection/ac-conversion-validation.yaml` identifies
records used to exercise importer and schema behavior, not a sample dataset. Scenario assets have
exactly one root and identity boundary:

```text
assets/scenarios/{native_asset_id}/
```

Generator and Policy Adapters are code capabilities, not another dataset. Only a concrete attack
variant generated through an approved Adapter and then frozen as project data enters
`assets/scenarios/`. Promptfoo selectors, Collections, aliases, and implementation/source references
produce no Scenario Asset.

This task documents those boundaries but creates no native output. Every ledger line therefore has
`native_output_kind: null` and `native_output_id: null`.

Formal evaluation defaults to:

```text
all assets where status=validated and eval_eligible=true
```

CI, smoke, regression, and debugging may select a subset only by referencing native IDs, tags, or
filters over the same canonical collection. No selection may duplicate scenario content. The
project does not create `benchmark_dataset/`, `promptfoo_dataset/`, `small_dataset/`, or
`full_dataset/`.

## Record Roles

Every ledger row has exactly one `record_role`:

- `benchmark_scenario`: an upstream security benchmark task or structured attack scenario;
- `normal_task_fixture`: a normal task/environment unit that can anchor a future security case;
- `attack_taxonomy`: an attack category without a record-level executable scenario;
- `attack_generation_entry`: a concrete Promptfoo Plugin, Collection, or alias selector;
- `delivery_strategy_entry`: a Promptfoo Strategy, preset, collection, alias, or deprecated stub;
- `implementation_reference`: implementation evidence that is not scenario data; or
- `source_reference`: provenance, license, configuration, or framework-source evidence that is not
  scenario data.

`source_asset_kind` refines the role. Promptfoo values include `plugin`, `plugin_collection`,
`plugin_alias`, `strategy`, `strategy_preset`, `strategy_collection`, `strategy_alias`, and
`deprecated_strategy_stub`. Reference values distinguish source code, configuration, license, and
documentation evidence. A role changes neither the source identity nor the one-ledger rule.

## Discovery Boundaries and Counts

All checkouts are read-only inputs. Before discovery, each checkout must exist, be clean, be a
complete non-partial clone, and match its locked repository and commit. The A/C benchmark locks come
from `references/source-locks/ac-reference-sources.yaml`; the Promptfoo capability lock comes from
`references/manifest.yaml`.

| Source | Discovery unit | Count | Record role |
|---|---|---:|---|
| SABER | Every JSON task reconciled between `dataset/manifest.json` and `tasks/` | 716 | `benchmark_scenario` |
| Inspect Evals / CodeIPI | Every embedded record in `src/inspect_evals/ipi_coding_agent/dataset/samples.json` | 45 | `benchmark_scenario` |
| Terminal-Bench 2 | Every top-level task directory at the locked commit | 89 | `normal_task_fixture` |
| MCP-SafetyBench | Every JSON attack task under `mcpuniverse/benchmark/configs/test/*/*.json` | 245 | `benchmark_scenario` |
| MCPSecBench structured | Every structured record in `data/data.json` | 11 | `benchmark_scenario` |
| MCPSecBench taxonomy | Every declared category not represented by a structured record | 6 | `attack_taxonomy` |
| Promptfoo Plugin selectors | 155 concrete IDs, 16 Collections, and 120 alias-only selectors | 291 | `attack_generation_entry` |
| Promptfoo Strategy identifiers | 37 accepted IDs plus registry-only deprecated `simba` | 38 | `delivery_strategy_entry` |
| Harbor | The 8 files named in its source-lock `audited_files` | 8 | `implementation_reference` |
| MCP-Universe | The 15 files named in its source-lock `audited_files` | 15 | `source_reference` |

The role coverage derived from those discovery results is:

```yaml
coverage_summary:
  benchmark_scenario_records: 1017
  normal_task_fixture_records: 89
  attack_taxonomy_records: 6
  attack_generation_entry_records: 291
  delivery_strategy_entry_records: 38
  implementation_reference_records: 8
  source_reference_records: 15
  ledger_total: 1464
```

Promptfoo entry kinds are reported separately from Record Role totals:

```yaml
promptfoo_summary:
  concrete_plugin_ids: 155
  plugin_collection_ids: 16
  alias_only_plugin_selectors: 120
  unique_plugin_entries: 291
  accepted_strategy_ids: 37
  registry_only_strategy_stubs: 1
  strategy_entries: 38
```

`ledger_total` is generated by summing role counts. It is not a scenario count and must not be a
handwritten generator constant. The observed value for the locked commits is 1464. Before Promptfoo
was added, 1135 meant 1112 benchmark/task/taxonomy source records plus 23 references; it never meant
1135 executable security scenarios. The revised ledger contains 1017 benchmark-scenario records,
89 normal-task fixtures, 329 Promptfoo Plugin/Strategy ledger entries, and 23 reference-only
records, with 6 taxonomy records accounting for the remainder.

MCP-SafetyBench dataset YAML files are orchestration manifests and do not become additional task
records. Supporting source files do not become task records. Harbor and MCP-Universe remain in
their established reference roles; their framework files must never be represented as scenarios.

SABER has a stronger reconciliation gate. Its manifest must contain 716 unique task IDs, the task
tree must contain 716 parseable JSON records, and the two ID sets must have no missing, extra, or
duplicate IDs. The expected scenario split is A=289, B=186, and C=241. Any mismatch fails generation
and reports the concrete IDs.

## Promptfoo Full Discovery

Promptfoo discovery parses source registries without importing or executing upstream modules. The
authoritative surfaces are:

- `src/redteam/constants/plugins.ts` for concrete Plugin IDs, Collections, remote-only markers,
  dataset-backed markers, and MCP group membership;
- `src/redteam/constants/codingAgents.ts` for Coding Agent IDs and Collection expansion;
- `src/redteam/constants/frameworks.ts` for Plugin aliases and alias-to-Plugin/Strategy expansion;
- `src/redteam/constants/strategies.ts` for accepted Strategy IDs, presets, collections, remote
  requirements, and multi-turn/agentic groups;
- `src/redteam/strategies/index.ts` for concrete Strategy registry entries and deprecated stubs;
- the referenced Plugin/Strategy/provider modules for local generation, target feedback, state,
  remote inference, and runtime ownership; and
- root and nested license or dataset provenance files for code and embedded-data disposition.

One `attack_generation_entry` row is emitted for each unique accepted Plugin selector. When an ID
appears in more than one selector class, one row is emitted with the runtime-precedence kind. At the
locked commit, `bias` is both an alias and a Collection, so it emits one `plugin_collection` row.
Concrete Plugin IDs, Collections, aliases, and expansion relations are therefore complete without
double counting. Collection and alias entries are selectors, not independent generation
implementations.

One `delivery_strategy_entry` row is emitted for each accepted Strategy ID plus a separate
unsupported row for the registry-only `simba` stub. Presets, Collections, and aliases retain their
expansion or alias relation; they do not become independent native implementations.

Every Promptfoo entry row records:

- the concrete ID and `source_asset_kind`;
- Collection membership, alias target, or expansion members;
- local-only, local-or-remote, or remote-only generation dependency;
- whether target feedback is required;
- `state_scope` as `none`, `per_candidate`, `per_run`, or `cross_run`;
- whether remote inference is required;
- current runtime ownership as `project` or `promptfoo_bound`;
- Repo/Shell, MCP, and future-domain applicability;
- root license and any embedded dataset or prompt-source provenance;
- native reuse classification; and
- grader bindings as `AUXILIARY_EVIDENCE` only.

The scan does not count Target Providers, the complete Eval Runtime, Campaign lifecycle, or graders
as generator or delivery capabilities. A grader binding may be recorded on its Plugin/Strategy row,
but it can never become the project Oracle.

## Index Contract

`references/upstream-index/ac-upstream-asset-index.jsonl` contains one JSON object per discovery
unit. Every object contains these common fields:

```json
{
  "source_project": "",
  "source_repository": "",
  "source_commit": "",
  "source_path": "",
  "source_record_key": "",
  "source_record_digest": "",
  "record_role": "",
  "source_asset_kind": "",
  "asset_family": "",
  "scenario_class": "",
  "category": "",
  "attack_present": null,
  "attack_origin": null,
  "attack_delivery_mode": null,
  "raw_reuse_disposition": "",
  "native_conversion_disposition": "",
  "conversion_reason": "",
  "native_output_kind": null,
  "native_output_id": null
}
```

Paths are repository-relative POSIX paths. Digests are lowercase 64-character SHA-256 hex values.
The three attack fields are populated only when upstream metadata supports the claim; absence or
ambiguity remains JSON `null`. Reference-only rows use `scenario_class: "reference_only"`.

Promptfoo Strategy rows additionally require non-null values for:

```json
{
  "requires_target_feedback": false,
  "state_scope": "none",
  "remote_inference_required": false,
  "runtime_ownership": "project",
  "reuse_classification": "GENERATOR_ADAPTER_REUSE"
}
```

For non-Strategy rows, these fields are present with JSON `null`, so the ledger has one stable
schema. Every Promptfoo entry row also has these exact fields:

```json
{
  "plugin_collection_ids": [],
  "expands_to_plugin_ids": [],
  "expands_to_strategy_ids": [],
  "alias_of": null,
  "generation_dependency": "local_only|local_or_remote|remote_only|not_applicable",
  "repo_shell_applicable": null,
  "mcp_applicable": null,
  "future_domain_only": null,
  "embedded_data_sources": [],
  "embedded_data_license_disposition": "",
  "grader_disposition": "AUXILIARY_EVIDENCE"
}
```

Non-Promptfoo rows use null or empty values for these fields. Expansion arrays contain IDs only,
not upstream prompt content. `embedded_data_sources` contains safe path, repository, commit, and
license metadata only.

After conversion or adaptation, `native_output_kind` may be `scenario_asset`, `generator_adapter`,
`policy_adapter`, or `none`; `native_output_id` identifies that concrete output. Both fields remain
null in the initial ledger because no native output exists yet. The allowed mapping is typed:

- reconstructed benchmark scenarios and normal-task fixtures may become `scenario_asset`;
- concrete Plugin or concrete Strategy entries may become `generator_adapter` or `policy_adapter`
  only when their conversion disposition approves that Adapter class;
- attack taxonomies, Plugin Collections, aliases, Strategy presets, Strategy Collections, Strategy
  aliases, deprecated stubs, and implementation/source references resolve to `none`; and
- no upstream row is forced to produce a Scenario Asset.

Lines are deterministic: source projects follow lock order, then records sort by `record_role`,
`source_path`, and `source_record_key`. JSON uses UTF-8, sorted keys, compact separators, and one
trailing newline per object. The index includes no host absolute path or scan timestamp.

## License and Native Conversion

Raw reuse and native conversion are independent dimensions.

`raw_reuse_disposition` is one of:

- `allowed`
- `review_required`
- `prohibited`
- `not_applicable`

It answers whether upstream raw content can be copied or redistributed. Promptfoo's root MIT license
does not automatically cover every embedded dataset, generated output, model service, or third-party
prompt source; those are recorded per Promptfoo entry.

`native_conversion_disposition` is one of:

- `eligible_for_semantic_reconstruction`
- `direct_import_allowed`
- `generator_adapter_candidate`
- `policy_adapter_candidate`
- `design_reference_only`
- `unsupported`
- `duplicate`
- `intentionally_excluded`
- `malformed`
- `conversion_failed`

It answers how the project may build or adapt native behavior. A restricted raw-reuse disposition
does not prevent project-authored semantic reconstruction. In particular, SABER, CodeIPI,
Terminal-Bench 2, MCP-SafetyBench, and structured MCPSecBench records are
`eligible_for_semantic_reconstruction` even when raw reuse requires review.

For example:

```yaml
saber:
  raw_reuse_disposition: review_required
  native_conversion_disposition: eligible_for_semantic_reconstruction
```

The initial native-conversion accounting for the locked ledger is:

```yaml
native_conversion_summary:
  eligible_for_semantic_reconstruction: 1106
  direct_import_allowed: 0
  generator_adapter_candidate: 174
  policy_adapter_candidate: 10
  design_reference_only: 169
  unsupported: 3
  duplicate: 2
  intentionally_excluded: 0
  malformed: 0
  conversion_failed: 0
```

This accounting comprises:

- 1106 benchmark scenarios and normal-task fixtures eligible for project-authored reconstruction;
- 154 concrete Promptfoo generator Plugins plus 20 concrete Strategy generator candidates;
- `agentic:memory-poisoning` plus 9 Strategy policy candidates;
- 6 MCPSecBench taxonomy inputs, 16 Plugin Collections, 118 mapped alias-only selectors, 6
  Strategy design references, and 23 Harbor/MCP-Universe references as design-only evidence;
- 2 unmapped Plugin aliases plus `simba` as unsupported; and
- 2 deprecated Strategy aliases as duplicates of their canonical Strategy IDs.

Raw reuse counts are reported separately and are derived only after each Promptfoo embedded-data
and remote-generation provenance check. They do not enter native-conversion conservation.

## Promptfoo Strategy Decisions

The ledger applies the strongest behavior in a preset or composition: if any expansion may call a
target, require remote inference, or carry cross-Run state, the selector row records that stronger
property. This fail-closed rule prevents a mixed selector from being approved as a static adapter.

| Strategy IDs | Count | Target feedback | State scope | Remote inference | Runtime ownership | Native conversion |
|---|---:|---:|---|---:|---|---|
| `base64`, `basic`, `camelcase`, `emoji`, `hex`, `homoglyph`, `image`, `jailbreak-templates`, `leetspeak`, `morse`, `piglatin`, `rot13`, `video` | 13 | no | `none` | no | `project` | `generator_adapter_candidate` |
| `audio`, `citation`, `gcg`, `jailbreak:composite`, `jailbreak:likert` | 5 | no | `per_candidate` | yes | `project` | `generator_adapter_candidate` |
| `math-prompt`, `multilingual` | 2 | no | `per_candidate` | no | `project` | `generator_adapter_candidate` |
| `other-encodings` | 1 | no | `none` | no | `project` | `design_reference_only` Collection |
| `prompt-injection` | 1 | no | `none` | no | `project` | `duplicate` of `jailbreak-templates` |
| `authoritative-markup-injection`, `best-of-n`, `goat`, `indirect-web-pwn`, `jailbreak:meta` | 5 | yes | `per_run` | yes | `promptfoo_bound` | `policy_adapter_candidate` |
| `crescendo`, `custom`, `jailbreak:tree`, `mischievous-user` | 4 | yes | `per_run` | no | `promptfoo_bound` | `policy_adapter_candidate` |
| `default` | 1 | yes | `per_run` | yes | `promptfoo_bound` | `design_reference_only` mixed preset |
| `layer`, `jailbreak:goblin`, `jailbreak:hydra` | 3 | yes | `cross_run` | yes | `promptfoo_bound` | `design_reference_only` |
| `retry` | 1 | yes | `cross_run` | no | `promptfoo_bound` | `design_reference_only` |
| `jailbreak` | 1 | yes | `per_run` | yes | `promptfoo_bound` | `duplicate` of `jailbreak:meta` |
| `simba` | 1 | no | `none` | no | `project` | `unsupported` registry-only no-op |

The 37 accepted IDs therefore contain 22 target-independent Strategy IDs and 15 IDs that
require target feedback or prior target results. Four IDs can carry cross-Run state:
`jailbreak:hydra`, `jailbreak:goblin` through Hydra inheritance, `layer` through adaptive provider
composition, and `retry` through prior-evaluation storage. The 38th ledger row is the unsupported
`simba` stub.

`GENERATOR_ADAPTER_REUSE` means a project-owned adapter may invoke or independently reproduce only
the generation/transform phase. `POLICY_ADAPTER_CANDIDATE` means a later adapter must prove that all
feedback and state stay inside one project Run. `DESIGN_REFERENCE` means no Promptfoo execution path
is adopted. `REJECT` applies when the capability cannot satisfy project ownership or isolation.
The ledger maps `generator_adapter_candidate` to `GENERATOR_ADAPTER_REUSE`,
`policy_adapter_candidate` to `POLICY_ADAPTER_CANDIDATE`, `design_reference_only` and `duplicate` to
`DESIGN_REFERENCE`, and `unsupported` to `REJECT`.

## Promptfoo Runtime Boundary

Promptfoo may supply attack-generation and transformation capability. It may not own or bypass:

- the Campaign Controller;
- the Agent Adapter or any Target Provider;
- Sandbox lifecycle or egress policy;
- Run-level state isolation;
- project-native utility and security Oracles;
- cost, call, turn, or time budgets; or
- Trace, tool-call, environment-effect, and receiver-side evidence capture.

Adaptive Promptfoo code cannot be reused merely because it exists. A policy candidate must expose
the next candidate through a narrow project adapter and receive only bounded, attacker-safe feedback
inside the current Run. It cannot persist state under a Promptfoo scan ID, read prior Eval results,
or call the target through `context.originalProvider` outside the Agent Adapter.

Hydra, Goblin, generic `layer`, and `retry` are design references at this stage because their locked
implementations can share scan/evaluation state or depend on Promptfoo-owned result storage. Meta,
Tree, Crescendo, Custom, GOAT, Best-of-N, Mischievous User, Authoritative Markup Injection, and
Indirect Web Pwn remain policy candidates only; none is approved for execution by this design.

Promptfoo grader output is `AUXILIARY_EVIDENCE`. It may support triage or progress feedback but may
not replace the project Final Assertion Engine, utility Oracle, deterministic verifier, or
receiver/environment effect evidence.

Future attack variants generated through an approved adapter enter the same canonical asset root
and record at least:

```yaml
derivation:
  parent_native_asset_id: ""
  generator: promptfoo
  promptfoo_commit: fcde2e89a89dc4ca79dcc3012927f50193251759
  plugin_id: ""
  strategy_id: ""
  attacker_model: ""
  generation_config_digest: ""
  random_seed: ""
  output_digest: ""
```

This provenance does not create a Promptfoo dataset or second native asset collection.

## Digest Rules

Digesting identifies each discovery unit without copying its content:

- SABER JSON tasks: SHA-256 of canonical JSON using sorted keys, compact separators, and UTF-8.
- CodeIPI embedded records: the same canonical JSON digest, one digest per array record.
- MCP-SafetyBench JSON tasks: the same canonical JSON digest, one digest per task file.
- Terminal-Bench 2 task directories: recursively enumerate every regular file in repository-relative
  POSIX order, compute each raw file SHA-256, serialize each entry as `path:file_sha256\n`, and hash
  the concatenated UTF-8 manifest. Symlinks, unreadable entries, and path escape fail closed.
- MCPSecBench structured records: the canonical JSON digest of each record.
- MCPSecBench taxonomy-only assets: SHA-256 of the normalized source path, record key, and declared
  category joined with newline characters.
- Promptfoo entry records: SHA-256 of a canonical source descriptor containing the ID,
  source kind, registration path, registry presence, membership/alias/expansion IDs, and source-only
  dependency flags. Project conversion judgments are excluded from the digest.
- Harbor and MCP-Universe references: raw file SHA-256.

Source scripts, Dockerfiles, setup commands, evaluators, Target Providers, and cleanup code are
never executed while discovering or digesting.

## Coverage and Conservation

`references/upstream-index/ac-upstream-coverage.yaml` is derived from the same in-memory record list
as the JSONL ledger. It is not maintained as an independent manual count. Every project records
`discovered_total`, `indexed_total`, counts by `record_role`, counts by raw-reuse disposition, and
counts by native-conversion disposition.

Every source satisfies:

```text
indexed_total = discovered_total
```

Native conversion is mutually exclusive and satisfies:

```text
discovered_total
= eligible_for_semantic_reconstruction
+ direct_import_allowed
+ generator_adapter_candidate
+ policy_adapter_candidate
+ design_reference_only
+ unsupported
+ duplicate
+ intentionally_excluded
+ malformed
+ conversion_failed
```

Raw reuse is independently mutually exclusive and satisfies:

```text
discovered_total
= allowed
+ review_required
+ prohibited
+ not_applicable
```

Raw-reuse counts never enter the native-conversion equation. Role counts independently sum to
`ledger_total`. The coverage file preserves these known source reconciliations:

```yaml
saber: 716
codeipi: 45
terminal_bench_2: 89
mcp_safetybench: 245
mcpsecbench_structured: 11
mcpsecbench_taxonomy: 6
promptfoo_concrete_plugins: 155
promptfoo_plugin_collections: 16
promptfoo_alias_only_selectors: 120
promptfoo_accepted_strategies: 37
promptfoo_registry_only_strategy_stubs: 1
harbor_references: 8
mcp_universe_references: 15
```

The SABER coverage entry additionally records `expected_upstream_total: 716`. Generation fails if
its discovered or indexed total differs from 716.

## Validation Selection Semantics

`references/import-selection/ac-seed-selection.yaml` moves to
`references/validation-selection/ac-conversion-validation.yaml`. Its 18 records remain provenance-
locked conversion and schema validation records. Existing semantic corrections, authorization
contexts, assertion applicability, and reconstruction constraints remain intact.

These 18 conversion-validation source records are a subset of the full upstream ledger. They are
not native assets and do not define a second or smaller dataset. Only native outputs later derived
from them may enter the canonical native scenario collection.

The file and Spike documentation replace dataset-like terms such as `seed selection`, `fixed input
set`, and `selected candidates` with the precise terms `conversion validation records`, `schema
validation records`, and `smoke execution IDs`. A validation record may point to an upstream ledger
record and a proposed conversion shape, but it may not embed a second copy of a canonical scenario.
Smoke execution IDs are native Scenario Asset IDs only and become usable only after those native
assets exist.

## Failure Handling

Discovery and ledger generation fail before replacing committed output when any of these occurs:

- a checkout is absent, dirty, shallow, partial, at a different commit, or has a different remote
  identity;
- a path is absolute, escapes its checkout, is unreadable, or violates the source-specific shape;
- SABER manifest and task IDs differ, repeat, or do not total 716;
- a Promptfoo source registry cannot be parsed without executing upstream code;
- a Promptfoo selector, alias, Collection, Strategy, preset, or registry-only stub disappears from
  accounting without an explicit disposition;
- a Record Role or `source_asset_kind` maps to a prohibited `native_output_kind`;
- the same source-project/path/record-key identity is emitted twice without a `duplicate`
  disposition;
- a required digest is not a valid SHA-256 value;
- any required JSONL field is absent or has the wrong type;
- `indexed_total` differs from `discovered_total`;
- a source's native-conversion or raw-reuse conservation equation fails; or
- the generated `ledger_total` differs from the sum of generated role counts.

A source record that is itself malformed or unsupported can still be indexed safely with that
disposition when its path, key, and digest are determinable. An enumeration failure that prevents
the record from being counted is fatal and cannot be hidden in `malformed`.

## Verification

Verification uses structured JSON, YAML, and TypeScript AST parsing and checks:

1. Every JSONL object has the common schema and Promptfoo Strategy rows have all five required
   runtime-classification fields.
2. Role counts satisfy `1017 + 89 + 6 + 291 + 38 + 8 + 15 = 1464`; the locked-source observation
   is 1464 ledger rows, not 1464 scenarios.
3. Native-conversion counts satisfy `1106 + 174 + 10 + 169 + 3 + 2 = 1464`, with zero in the
   remaining dispositions.
4. Each source count matches the discovery table and every row matches the locked repository and
   commit.
5. SABER has 716 unique reconciled IDs with the A/B/C split 289/186/241.
6. Promptfoo has 155 concrete Plugin IDs, 291 unique accepted Plugin selectors, 37 accepted
   Strategy IDs, and one registry-only `simba` stub; Collection and alias expansions reconcile.
7. Collection, alias, preset, and stub rows are not counted as concrete capabilities. Only concrete
   Promptfoo Plugin or Strategy rows may have an Adapter Candidate conversion disposition.
8. Selector and implementation/source reference rows resolve to future `native_output_kind: none`;
   benchmark, fixture, and taxonomy rows never map directly to `generator_adapter`.
9. Every digest matches a fresh read-only scan of the locked checkout.
10. Every project satisfies indexed/discovered equality and both independent conservation
    equations.
11. All initial `native_output_kind` and `native_output_id` values are null, and no
    `assets/scenarios/` content is created.
12. The renamed validation file still has exactly 18 validation records and contains no claim that
    those records define dataset scope.
13. Repository search finds no second dataset or copied-scenario path, no remaining references to
    the removed import-selection path, and no prohibited dataset-like terminology in the changed
    A/C documents.
14. The diff touches only documentation and reference metadata; runtime code remains unchanged.
15. Existing Ruff, formatting, MyPy, non-Docker tests, and PyRIT checks continue to pass.

The branch is ready for another specification review only after this revision is committed and
pushed. No implementation plan, upstream JSONL ledger, coverage YAML, or canonical native asset is
created before that review passes.

## Source Family Decisions

| Source family | Record role | Full discovery | Future native output |
|---|---|---|---|
| SABER | benchmark scenario | yes | project-authored scenario |
| CodeIPI | benchmark scenario | yes | project-authored scenario |
| Terminal-Bench 2 | normal task fixture | yes | environment/task fixture |
| MCP-SafetyBench | benchmark scenario | yes | project-authored MCP scenario |
| MCPSecBench structured | benchmark scenario | yes | project-authored MCP scenario |
| MCPSecBench taxonomy | attack taxonomy | yes | no runtime output; generator/category input only |
| Promptfoo concrete Plugin | attack-generation entry | yes | Generator/Policy Adapter candidate |
| Promptfoo Plugin Collection/alias | attack-generation entry | yes | no native runtime output |
| Promptfoo concrete Strategy | delivery-strategy entry | yes | transformer/Run-policy Adapter candidate |
| Promptfoo Strategy preset/Collection/alias/stub | delivery-strategy entry | yes | no native runtime output |
| Harbor | implementation reference | yes | no scenario |
| MCP-Universe | source reference | yes | no scenario unless separately approved |
