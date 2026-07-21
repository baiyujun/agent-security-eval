# ADR-0002: Import External Benchmarks Offline into a Project-Native Runtime

- Status: Accepted
- Date: 2026-07-17

## Context

External security and Agent benchmarks contain valuable scenario knowledge, task assets, fixtures,
attack placements, and Oracle designs. They also expose incompatible task types, execution loops,
tool protocols, state models, result semantics, cleanup behavior, dependency stacks, and release
cadences.

Making several upstream runtimes part of the production execution path would require the project to
preserve those incompatible semantics indefinitely. A change in an upstream task class, runner, or
Scorer could then alter production behavior without changing the project's own scenario contract.
It would also make an upstream result appear authoritative even when its Oracle observes a weaker
security endpoint than the project requires.

The project needs a stable boundary that preserves useful upstream knowledge and provenance without
turning external runtime objects into its persistent domain model.

## Decision

Treat each external Benchmark as a **source language** and the project Scenario Pack as the
**internal representation and target format**. An Offline Benchmark Importer is a compiler
frontend. The project runtime is the sole production runtime.

```text
External Benchmark = source language
Project Scenario Pack = internal IR / target format
Offline Benchmark Importer = compiler frontend
Project runtime = sole production runtime
```

```text
external source at a pinned commit
  -> Offline Benchmark Importer
  -> validated project-native Scenario Pack
  -> ScenarioCase compilation/materialization
  -> project runtime
  -> project-native observations and assertions
```

External material may be reused in one of four explicit modes:

- `reference_only`: use taxonomy, architecture, threat models, or scenario ideas without importing
  code or assets.
- `asset_import`: transform selected, licensed upstream tasks or fixtures offline into native,
  provenance-bearing assets.
- `code_internalization`: internalize only a small, stable, single-purpose implementation whose
  license and attribution obligations are clear.
- `upstream_replay`: run the pinned upstream system only for paper reproduction or Importer
  consistency checks, outside the production execution path.

An imported pack must be loadable and executable without importing the upstream Benchmark package.
Upstream types, runner state, and result objects do not enter the persistent project model. Imported
or internalized material must record its repository, exact commit, upstream paths, applicable
license, transformation, and local ownership.

`reuse_mode` records how source material may cross the project boundary. `asset_role` separately
records what the resulting native material is used for. Asset roles include scenario template,
attack seed, normal-task fixture, Oracle candidate, and taxonomy. Neither field selects a production
runtime backend.

The full `BaseScenario` and `ScenarioCase` model belongs to the scenario-assets boundary. Existing
`ExecutionScenarioSpec` and `ExecutionRunSpec` remain execution-owned contracts. M1-A will define a
separate compilation/materialization boundary from `ScenarioCase` to the minimum execution and
policy inputs, preserving normal task, attacker objective, and concrete attack candidate as distinct
values.

## Consequences

### Benefits

- Production execution has one lifecycle, trace model, assertion model, and cleanup contract.
- Upstream API and dependency changes are contained in offline tooling or replay environments.
- Scenario Packs can be reviewed, versioned, reproduced, and migrated independently of an upstream
  runner release.
- Task utility and security effects can be re-adjudicated with project-native evidence instead of
  inheriting an upstream Score as final truth.
- License and provenance decisions occur before material reaches the runtime path.
- Scenario assets can evolve without forcing source-specific fields into every execution backend.

### Costs

- Each supported source format needs a bounded Importer and conversion tests.
- Importers must preserve source semantics while reporting information that cannot be represented
  safely.
- Upstream replay environments remain necessary for selected conversion checks and paper
  reproduction.
- Imported packs may need regeneration when the native schema changes or when a new upstream commit
  is deliberately adopted.

## Dependency Rules

The allowed dependency direction is:

```text
importer -> project-native scenario schema
compiler -> project-native scenario schema + execution contracts
runtime  -> execution contracts

runtime  -X-> importer
runtime  -X-> external Benchmark runtime
scenario schema -X-> execution integration internals
importer -X-> production runtime internals
```

These rules apply even when an upstream project offers a convenient Python API:

1. Production runtime modules must not import SABER, Harbor, AgentDojo, AppWorld,
   MCP-SafetyBench, or another Benchmark package.
2. Production runtime modules must not import Importer modules.
3. Importers may depend on source-specific parsers and the project-native scenario schema, but may
   not own runtime scheduling, execution, observation, or adjudication.
4. Persisted entities and public Scenario Pack fields use project vocabulary. Serialized upstream
   objects are not an escape hatch.
5. Upstream reference actions, Scorers, or result labels are evidence inputs or Oracle candidates,
   not the project's final security truth.
6. `upstream_replay` runs in a separately provisioned environment and cannot be selected as a
   production Campaign Backend.
7. A generated Scenario Pack must load and validate without the upstream package installed.

Long-lived runtime classes such as `SaberExternalBenchmarkAdapter`, `AgentDojoRuntimeAdapter`,
`HarborRuntimeAdapter`, `AppWorldRuntimeAdapter`, and
`InspectEvalsExternalBenchmarkAdapter` are therefore prohibited.

## Terminology

Only these integration terms are used in current architecture documents:

- **Target Adapter**: connects the evaluated Agent and emits project-owned observations.
- **Offline Benchmark Importer**: parses and converts pinned upstream material without executing it.
- **Upstream Replay Harness**: runs a pinned upstream system in isolation for parity or reproduction.

The unqualified term `Benchmark Adapter` is avoided because it obscures whether a component parses
assets or owns a runtime lifecycle.

## Rejected Alternatives

### Chain multiple Benchmark runtimes at execution time

Rejected because it creates several lifecycle and isolation authorities, multiplies operational
dependencies, and makes behavior depend on upstream release state.

### Persist upstream task and result objects

Rejected because upstream schemas would become an accidental public contract. Core migrations and
runtime logic would then need to understand source-specific vocabulary and version drift.

### Treat an external Benchmark result as final security truth

Rejected because upstream Scorers observe different endpoints and may combine task utility,
assistant text, tool intent, tool execution, and environmental effects differently. The project
must retain its own assertion and evidence semantics.

### Maintain one production runtime adapter per Benchmark

Rejected because each adapter would be a shallow compatibility layer over a second execution
kernel. The apparent common interface would hide rather than remove incompatible environment,
trace, Oracle, and cleanup semantics.

### Copy complete upstream environments into the repository

Rejected because it obscures provenance, imports broad dependency and license obligations, and
creates an unowned fork. Only explicitly approved assets or small implementations may cross the
boundary.

## Migration Strategy

1. Record capability-level decisions in `references/manifest.yaml` and exact A/C source facts in
   `references/source-locks/ac-reference-sources.yaml` plus approved record selection in
   `references/import-selection/ac-seed-selection.yaml`.
2. Use `reference_only` until the source-level audit supports a more permissive mode. Unknown or
   mixed licenses block copying.
3. Define the `ScenarioCase -> CompiledRunInput / ExecutionRunSpec` boundary before broad Importer
   implementation.
4. Run small Offline Benchmark Importer spikes for representative sources. The spikes define
   minimum field candidates and loss reports; they do not freeze the complete domain model.
5. Compare selected imported cases with `upstream_replay` where practical. Differences must be
   explained as intentional normalization or treated as conversion failures.
6. Promote only self-contained, provenance-complete Scenario Packs to the project runtime.
7. Add dependency checks when Importer and scenario packages exist so the prohibited edges become
   mechanically enforced.
8. Re-import deliberately from a newly audited commit. Never let a floating upstream dependency
   change a released Scenario Pack in place.

No production Importer, replay harness, scenario model, registry, or runtime implementation is part
of this ADR's documentation phase.
