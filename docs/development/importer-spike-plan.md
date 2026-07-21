# Offline Benchmark Importer Spike Plan

- Status: Proposed; blocked on M1-A compiler-boundary review and per-asset rights gates
- Date: 2026-07-17
- Architecture decision: [ADR-0002](../adr/0002-offline-import-native-runtime.md)
- Source evidence: [Reference Reuse Audit](../architecture/reference-reuse-audit.md)
- Current A/C locks: `references/source-locks/ac-reference-sources.yaml`
- Current selection: `references/import-selection/ac-seed-selection.yaml`

## Go / No-Go

- **Judgment**: No-Go for implementation until M1-A and source approvals; Go for the bounded design.
- **Reason**: the two source formats, representative records, loss boundary, and replay role are
  understood, but no importer should invent the `ScenarioCase -> execution` compiler contract or
  copy rights-blocked source content.
- **Judgment owner**: M1-A reviewers own the compiler boundary; source reviewers approve each asset;
  project tests and conversion review judge a Spike complete.

## Target Result

S1 validates two offline conversion frontends:

1. `SaberImporterSpike`
2. `InspectEvalsCodeIPIImporterSpike`

The names describe validation work, not stable public classes. Each Spike reads 5-10 records from a
fixed commit and emits project-native Scenario Pack candidates with complete provenance and an
explicit conversion-loss report. The output must load and validate with no upstream package
installed.

When source execution is necessary for comparison, a separately provisioned Upstream Replay Harness
may run the pinned source. Replay is optional evidence and is never a production Campaign Backend or
final-security authority.

## Architecture Boundary

```text
fixed source record
  -> source-specific Offline Benchmark Importer Spike
  -> native Scenario Pack candidate + provenance + conversion loss
  -> project static validation
  -> M1-A compiler contract
  -> project execution runtime

fixed source runtime
  -> isolated Upstream Replay Harness
  -> parity evidence
  -X-> production runtime
```

The Importer does not start containers, execute setup commands, run verifiers or solutions, schedule
an Agent, collect production trace, adjudicate final assertions, or own cleanup.

## Shared Input Gates

Before a record may be read for `asset_import`:

1. Repository, full commit SHA, relative path, record key, and digest match the source lock and
   selection record.
2. The source checkout is clean and the content digest does not drift during the read.
3. Software license, data license, and file-level restrictions are recorded.
4. `REVIEW_REQUIRED` material is limited to structure analysis or semantic reconstruction; raw text,
   payloads, fixtures, solutions, and code are not copied.
5. Source paths are repository-relative and confined; absolute paths, traversal, symlink escape, and
   unclassified files fail closed.
6. Source executable fields are parsed only as untrusted metadata and never run during import.

## Shared Output Candidates

These are comparison fields, not a frozen domain schema:

| Candidate | Purpose | Required property |
| --- | --- | --- |
| Source provenance | Reproduce repository/commit/path/record/digest/rights | No local host path |
| Lineage | Connect source fields to derived asset and project-authored extensions | Generator version and seed are explicit |
| Native scenario identity | Correlate a fixed case without using source paths as IDs | Project vocabulary only |
| Normal task | Preserve benign user intent | Separate from attacker objective |
| Attack objective | Preserve intended adversarial effect | Separate from concrete attack content |
| Attack placement/seed reference | Describe source-controlled channel and lineage | No raw payload required |
| Authorization context | State allowed/forbidden reads, outputs, sinks, and declassification | No implicit authorization propagation |
| Fixture intent | Describe files/services/state and roles | No arbitrary executable setup |
| Oracle candidates | Preserve utility, progress, effect, integrity, reset, and reproducibility intent | No upstream aggregate truth |
| Reset candidate | Restore all local mutable state | Post-reset equivalence assertions |
| Conversion-loss report | Record unknown/unmapped/degraded/blocked semantics | Never silently folded into provenance |

M1-A decides which of these values become `ScenarioCase`, compilation input, runtime input, or
supporting asset contracts.

## Shared Conversion Rules

1. **Fail closed**: missing fields, unknown schema versions, digest mismatch, or unsafe paths reject
   a record deterministically.
2. **No silent defaults**: unrepresentable semantics enter the loss report.
3. **Separate truth dimensions**: task utility, attack progress, security effects, control behavior,
   harness integrity, and final outcome remain distinct.
4. **No source types**: generated data and public loading APIs contain no Inspect `Sample`, SABER
   runtime object, or other upstream class.
5. **No upstream load dependency**: generated candidates load with only project dependencies.
6. **Deterministic content**: the same source tuple and Importer version produce the same content
   digest; timestamps are excluded from content identity.
7. **Private roles remain private**: solutions, hidden tests, reference answers, and verifier secrets
   never enter Agent-visible material.
8. **Project extensions are honest**: synthetic Canary, receiver, secret store, effect marker, and
   local service fields are labelled project-authored rather than attributed upstream.

## Spike 1: SaberImporterSpike

### Fixed Source

- Repository: `https://github.com/sssr-lab/SABER`
- Commit: `bfdffb10c3887b38e1bd57ae2e548faa8f2049e9`
- Rights: task-data license conflict remains `REVIEW_REQUIRED`

### Representative Set

The current six-record comparison set is:

| Scenario | Record | Source path | Role |
| --- | --- | --- | --- |
| A | `A_info_001` | `tasks/A/info_leak/A_info_001.json` | indirect injected information risk |
| A | `A_code_041` | `tasks/A/code_tampering/A_code_041.json` | indirect injected code risk |
| B | `B_info_001` | `tasks/B/info_leak/B_info_001.json` | unsafe-choice control, no attack |
| B | `B_code_001` | `tasks/B/code_tampering/B_code_001.json` | unsafe-choice control, no attack |
| C | `C_info_001` | `tasks/C/info_leak/C_info_001.json` | direct user attack |
| C | `C_code_001` | `tasks/C/code_tampering/C_code_001.json` | direct user attack |

These records may be structurally profiled before rights approval. Raw import or redistribution is
blocked until the SABER root/dataset license conflict is resolved for the selected paths.

### Conversion Proof

The Spike must show that it can:

- distinguish normal task, direct attack, indirect injection, and no-attack unsafe choice;
- represent fixture intent without executing `init_commands` or source runtime code;
- preserve injection channel/placement and harm description as reviewable intent;
- keep `harmful_command_patterns` and `expected_safe_commands` as non-authoritative assertion
  candidates or loss entries;
- report simulated network, Git, package-manager, shell, and state-delta semantics that cannot be
  transferred faithfully;
- generate deterministic native candidates that load without SABER installed.

### Optional Replay Comparison

If rights and isolation allow, run the six fixed records in a temporary pinned SABER checkout to
compare normal-task text, fixture intent, source event categories, and source Score polarity. Do not
compare aggregate source success as project final truth. Replay containers are destroyed after each
case, have no production credentials, and cannot feed the Campaign Controller.

### Stop Conditions

- Rights remain unclear for any attempted raw asset transfer.
- Conversion requires trusting simulated source output as receiver/environment truth.
- Scenario B/C meaning requires guessed defaults.
- Generated candidates depend on SABER packages or runtime files.

## Spike 2: InspectEvalsCodeIPIImporterSpike

### Fixed Source

- Repository: `https://github.com/UKGovernmentBEIS/inspect_evals`
- Commit: `3fda7b008453f8ba6bb7b1471e8fbd1865d2257e`
- Dataset path: `src/inspect_evals/ipi_coding_agent/dataset/samples.json`
- Rights: samples and embedded repository fixtures remain `REVIEW_REQUIRED`

### Representative Set

| Type | Upstream ID | Purpose |
| --- | --- | --- |
| Issue | `ipi-issue-exfil-01-plain` | issue injection and exfiltration endpoints |
| Issue | `ipi-issue-exec-32-authority` | authority phrasing and execution endpoint |
| Comment | `ipi-comment-exec-01-plain` | source-comment injection |
| Comment | `ipi-comment-persist-12-authority` | persistence endpoint |
| README | `ipi-readme-exfil-16-authority` | README injection and disclosure/delivery distinction |
| Benign | `ipi-benign-02-suspicious` | false-positive and over-refusal control |

If a selected record fails rights approval, a same-type approved replacement may be proposed. The
`Issue 2 + Comment 2 + README 1 + Benign 1` distribution remains fixed for the Spike review.

### Conversion Proof

The Spike must show that it can:

- normalize sample identity, legitimate task intent, injection-vector metadata, fixture path
  manifests, verification intent, persistence targets, and provenance;
- reject absolute paths, traversal, symlink escape, unknown fields, and digest drift;
- emit references to semantically reconstructed fixture seeds instead of raw `repo_files` content;
- keep `verification_command` as private utility-Oracle intent;
- separate secret observation, assistant disclosure, exfiltration attempt, executed request,
  receiver delivery, code execution, and persistence effects;
- preserve benign false-positive semantics;
- generate deterministic native candidates that load without Inspect Evals or Inspect AI installed.

### Optional Replay Comparison

If approved, run only the fixed CodeIPI task in an isolated temporary checkout to compare task text,
fixture roles, verification intent, and the source Scorer's observed endpoint. The project records
where source scoring combines or omits endpoints. The source Score is never copied into a final
security field.

### Stop Conditions

- Sample or embedded fixture rights cannot be confirmed for the attempted transfer.
- A Scorer judgment cannot be mapped to a specific evidence endpoint.
- Conversion requires Inspect types in the native pack or production runtime.
- Source canaries, payloads, or repository contents would need to be copied without approval.

## Deferred Terminal-Bench Fixture Importer

`TerminalBenchFixtureImporter` is not part of the first two S1 Spikes. It remains a follow-up after
M1-A and asset-rights review. Any future plan must use the current source lock:

- Repository: `https://github.com/harbor-framework/terminal-bench-2`
- Commit: `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`
- Candidate paths: `regex-log`, `log-summary-date-ranges`, and `nginx-request-logging`
- Fixed-commit license: no root license present; raw asset reuse remains blocked

The old `harbor-framework/terminal-bench@d28711.../original-tasks/*` plan is superseded and must not
be implemented as the Terminal-Bench 2 source.

## Acceptance Evidence

Each initial Spike must provide:

1. 5-10 fixed records, with the planned six-record set preferred.
2. Complete source tuple, rights status, derivation, generator version, seed policy, and output digest.
3. Explicit conversion loss for every unknown, blocked, executable, or non-authoritative field.
4. No raw source content when rights permit only semantic reconstruction.
5. Deterministic repeated conversion.
6. Native-candidate loading and static validation without upstream packages.
7. Proof that normal task, attacker objective, concrete seed/candidate, utility Oracle, security
   Oracle, and final truth are not collapsed.
8. If replay is used, an isolated lifecycle record and an explicit statement that replay evidence is
   non-authoritative.

## First Execution Action

After M1-A, build a per-record source approval table for the twelve preferred SABER and CodeIPI
records. Do not create Importer code or copy source material until every attempted transfer has a
reviewable fixed tuple and rights disposition.
