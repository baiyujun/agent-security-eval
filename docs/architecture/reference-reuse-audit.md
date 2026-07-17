# Reference Source Audit and Reuse Boundary

- Audit baseline: 2026-07-16
- Alignment date: 2026-07-17
- Status: architecture evidence for proposed
  [ADR-0002](../adr/0002-offline-import-native-runtime.md)
- Scope: fixed-commit source findings, reuse boundary, rights gates, and provenance ownership
- Non-action: no third-party source, data, image, task record, fixture, or generated asset is copied
  by this document

## Conclusion

External Benchmarks are sources of scenario knowledge, task assets, fixtures, attack seeds, and
Oracle designs. They are not production execution kernels.

```text
pinned upstream source
  -> source-specific Offline Benchmark Importer
  -> provenance + conversion-loss report
  -> project-native Scenario Pack
  -> project validation and compilation
  -> sole project runtime

pinned upstream runtime
  -> isolated Upstream Replay Harness
  -> parity/reproduction evidence only
  -X-> production Campaign Backend
```

Only four source reuse modes are permitted:

- `reference_only`
- `asset_import`
- `code_internalization`
- `upstream_replay`

An upstream Score, label, reward, screenshot, command regex, model judgment, or simulated network
success is never the project's final security truth.

## Evidence Ownership

This document does not duplicate all source facts. The current sources of truth are:

| Evidence | Owner | Purpose |
| --- | --- | --- |
| Capability-level reuse decisions | `references/manifest.yaml` | Project role and accepted/rejected capabilities |
| Exact A/C source tuples and audited paths | `references/source-locks/ac-reference-sources.yaml` | Repository, commit, path, rights, and restrictions |
| Selected A/C candidate records | `references/import-selection/ac-seed-selection.yaml` | Fixed source IDs/digests and intended derivations |
| Detailed A/C source findings | `docs/reference-assets/ac-source-inventory.md` | Schema, lifecycle, trace, Oracle, reset, and reuse analysis |
| Current A/C draft boundary | `docs/development/ac-asset-ingestion-spike.md` | Native candidate fields, loss, rights, and no-runtime rules |
| M0 integration reference audit | `docs/reference-reuse-analysis.md` | Inspect AI, PyRIT, promptfoo, ClawSentry, and early source findings |

If prose here conflicts with a fixed tuple or restriction in the source-lock YAML, the source lock
wins. If an asset has no approval record, `reference_only` is the maximum allowed mode.

## Cross-Source Findings

### Upstream results observe different endpoints

SABER command patterns, CodeIPI Canary checks, AgentDojo injection success, Harbor rewards,
MCP-SafetyBench attack evaluators, and MCPSecBench labels do not mean the same thing. They may
produce candidate assertions or replay evidence, but they cannot be normalized into a single
upstream `safe/unsafe` field.

### Fixture, solution, and verifier roles must stay separate

Terminal-Bench 2 and Harbor explicitly separate instructions, environments, solutions, and
tests/verifiers. Native packs should preserve those roles. Calibration solutions and verifier
secrets must not enter Agent-visible fixtures, prompts, traces, or error messages.

### Live external services are not reproducible security truth

MCP-Universe tasks and some related Benchmarks call real services and carry cleanup risk. Native
security evaluation uses local synthetic services with snapshot/reset evidence. Live upstream
services may appear only in separately approved replay work.

### Conversion loss is part of the result

Importer output must explain unknown fields, unconverted executable setup, scorer semantics that
cannot be represented, rights blocks, and intentional normalization. A loss report cannot be hidden
inside generic provenance or replaced with guessed defaults.

## Current A/C Sources

Current details live in the source locks and A/C inventory. The fixed high-level dispositions are:

| Source | Fixed commit | Current role | Production runtime decision |
| --- | --- | --- | --- |
| SABER | `bfdffb10c3887b38e1bd57ae2e548faa8f2049e9` | A-class task/fixture/attack/Oracle intent source | Reject SABER runtime; offline semantic reconstruction only until rights resolve |
| Inspect Evals / CodeIPI | `3fda7b008453f8ba6bb7b1471e8fbd1865d2257e` | A-class coding injection sample and Scorer reference | Reject CodeIPI runtime/Scorer ownership; offline reconstruction |
| Terminal-Bench 2 | `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c` | A-class normal task/environment/verifier source | Reject legacy/Harbor runtime; raw assets blocked pending rights/image review |
| Harbor | `d3e606d9f7d1e111bb22d3d820ebed03ec300eb3` | Directory-role, mapper, verifier, and cleanup design | Design reference only; no nested lifecycle |
| MCP-SafetyBench | `7872437b6369aac1150e3a19e350a981dc554f81` | C-class attack schema/transition reference | Reconstruct local patterns; no source runtime, code, credential, or URL |
| MCP-Universe | `48b453021694d9823d308627fb7f6b7edd29541a` | C-class provenance/lifecycle reference | Design reference only; no live-service runtime |
| MCPMark submodule | `a684e7a3069f824bf5230a7cffe0a4de2add7f0d` | Local task/verifier design reference | Per-asset review before any import |
| MCPSecBench | `7612c5a3e811dcf01f64e4f2bb324591a2feaaf4` | C-class taxonomy and malicious-server concept source | Taxonomy/design reference; no GUI/runtime/data import |

The earlier PR #5 Terminal-Bench tuple
`harbor-framework/terminal-bench@d28711d0da2675d0bb1d56de45ae5df6082438a3` is not migrated as
the Terminal-Bench 2 asset source. Merged PR #6 replaced it with the official
`harbor-framework/terminal-bench-2@69671f...` full checkout and Harbor-native paths.

## Additional Stateful-Environment Evidence

These fixed audits remain architecture evidence but are not approved `asset_import` inputs in the
current A/C source-lock file.

### AgentDojo

- Repository: `https://github.com/ethz-spylab/agentdojo`
- Commit: `089ed468cf3ed0322acc66b0211f26d9d90dbf60`
- Root license: MIT with embedded third-party notices requiring per-asset review

Useful concepts include separate user/injection tasks, environment snapshots, utility/security
Oracle separation, injection slots, and state-based checks. Python task classes and YAML includes
are executable plugins, not safe static data. `security=True` means attack-goal success and must not
be reused with a system-safety polarity. AgentDojo runtime/pipeline ownership is rejected; fixed
upstream execution is replay-only.

### tau-bench lineage

- tau-bench repository: `https://github.com/sierra-research/tau-bench`
- tau-bench commit: `59a200c6d575d595120f1cb70fea53cef0632f6b`
- tau2-bench historical `v0.2.0`: `f8de30c298689cbe0117d76a378e7315a17e5bd8`
- current tau3 code in the tau2-bench repository:
  `a1e85084a3960281cb06997594133e8f39ea42a7`
- Root license: MIT; domain-data rights require separate review

Useful concepts include policy text, tool contracts, initial databases, task definitions, and
separate database/action/communication/assertion evaluation. Reference actions can construct an
expected end state and are not automatically the only acceptable call sequence. Natural-language
or LLM evaluation remains non-authoritative. The upstream runner, user simulator, and task types are
not production dependencies.

### AppWorld

- Repository: `https://github.com/StonyBrookNLP/appworld`
- Commit: `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`
- Public code license: Apache-2.0
- Protected bundle condition: public redistribution and derivatives may need to remain encrypted

Useful concepts include start/end state, entity diff, requirement assertions, no-op pass/fail, and
collateral-change checks. The first native version should re-express these ideas over small local
services. AppWorld's full apps, database, task bundles, evaluator, and runtime are not imported.
Protected bundle contents are not unpacked or copied by this project.

## ClawSentry Boundary

- Repository: `https://github.com/Elroyper/ClawSentry`
- Commit: `b5fe3a764e10e78f7fd5799cb9438896cdb60096`
- Release: `v0.8.6`
- Role: Beta engineering reference, not an architecture foundation

The project may re-express cross-framework capability descriptions, unified event vocabulary, and
deterministic trajectory-pattern ideas in project-owned contracts. It does not adopt ClawSentry's
Gateway, online decision chain, domain models, or concrete Codex/Gemini/framework adapters. No
ClawSentry package or event stream is a required runtime dependency.

## Importer Boundary

An Offline Benchmark Importer may:

- verify fixed repository/commit/path/digest tuples;
- parse source data without executing source code;
- normalize approved metadata and semantic intent;
- classify Agent-visible, verifier-private, solution, and setup roles;
- emit project-native draft assets, provenance, and conversion loss;
- reject unknown schemas, unsafe paths, executable setup, or unapproved material.

It may not:

- launch a source container, service, evaluator, solution, or cleanup routine;
- schedule Agents or own runtime lifecycle;
- emit upstream objects into the Scenario Pack;
- treat source regex, reward, Score, model judgment, or screenshot as final truth;
- copy material whose rights or provenance remain unresolved.

## Upstream Replay Boundary

Replay is separately provisioned, pinned, isolated, and non-authoritative. It is limited to:

- paper/result reproduction;
- Importer conversion parity;
- fixture/task/Oracle semantic checks;
- investigation of documented conversion loss.

Replay output is evidence attached to an import review. It cannot be selected as a production
Campaign Backend, cannot generate final security truth, and cannot make a source eligible for import
without independent rights/provenance approval.

## Next Decision

M1-A defines the native `ScenarioCase -> CompiledRunInput / ExecutionRunSpec` boundary. Only after
that boundary and per-asset rights gates may the two initial Offline Benchmark Importer spikes begin.
