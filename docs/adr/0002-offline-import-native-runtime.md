# ADR-0002: Import External Benchmarks Offline into a Project-Native Runtime

- Status: Accepted
- Date: 2026-07-16

## Context

External security and agent benchmarks contain valuable scenario knowledge, task assets, fixtures,
attack placements, and oracle designs. They also expose incompatible task types, execution loops,
tool protocols, state models, result semantics, cleanup behavior, dependency stacks, and release
cadences.

Making several upstream runtimes part of the production execution path would require the project to
preserve those incompatible semantics indefinitely. A change in an upstream task class, runner, or
scorer could then alter production behavior without changing the project's own scenario contract.
It would also make an upstream result appear authoritative even when its oracle observes a weaker
security endpoint than the project requires.

The project needs a stable boundary that preserves useful upstream knowledge and provenance without
turning external runtime objects into its persistent domain model.

## Decision

Treat each external benchmark as a **source language** and the project Scenario Pack as the
**internal representation and target format**. An importer is an offline compiler frontend. The
project runtime is the sole production runtime.

```text
External benchmark = source language
Project Scenario Pack = internal IR / target format
Importer = offline compiler frontend
Project runtime = sole production runtime
```

```text
external source at a pinned commit
  -> offline importer
  -> validated project-native Scenario Pack
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
- `upstream_replay`: run the pinned upstream system only for paper reproduction or importer
  consistency checks, outside the production execution path.

An imported pack must be loadable and executable without importing the upstream benchmark package.
Upstream types, runner state, and result objects do not enter the persistent project model. Imported
or internalized material must record its repository, exact commit, upstream paths, applicable
license, transformation, and local ownership.

## Consequences

### Benefits

- Production execution has one lifecycle, trace model, assertion model, and cleanup contract.
- Upstream API and dependency changes are contained in offline tooling or replay environments.
- Scenario Packs can be reviewed, versioned, reproduced, and migrated independently of an upstream
  runner release.
- Task utility and security effects can be re-adjudicated with project-native evidence instead of
  inheriting an upstream score as final truth.
- License and provenance decisions occur before material reaches the runtime path.

### Costs

- Each supported source format needs a bounded importer and conversion tests.
- Importers must preserve source semantics while reporting information that cannot be represented
  safely.
- Upstream replay environments remain necessary for selected conversion checks and paper
  reproduction.
- Imported packs may need regeneration when the native schema changes or when a new upstream commit
  is deliberately adopted.

## Dependency Rules

The allowed dependency direction is:

```text
importer -> project-native schema
runtime  -> project-native schema

runtime  -X-> importer
runtime  -X-> external benchmark runtime
importer -X-> production runtime internals
```

These rules apply even when an upstream project offers a convenient Python API:

1. Production runtime modules must not import SABER, Harbor, AgentDojo, AppWorld,
   MCP-SafetyBench, or another benchmark package.
2. Production runtime modules must not import importer modules.
3. Importers may depend on source-specific parsers and the project-native schema, but may not own
   runtime scheduling, execution, observation, or adjudication.
4. Persisted entities and public Scenario Pack fields use project vocabulary. Serialized upstream
   objects are not an escape hatch.
5. Upstream reference actions, scorers, or result labels are evidence inputs or oracle candidates,
   not the project's final security truth.
6. `upstream_replay` runs in a separately provisioned environment and cannot be selected as a
   production backend.

Long-lived runtime classes such as `SaberExternalBenchmarkAdapter`, `AgentDojoRuntimeAdapter`,
`HarborRuntimeAdapter`, and `AppWorldRuntimeAdapter` are therefore prohibited.

## Rejected Alternatives

### Chain multiple benchmark runtimes at execution time

Rejected because it creates several lifecycle and isolation authorities, multiplies operational
dependencies, and makes behavior depend on upstream release state.

### Persist upstream task and result objects

Rejected because upstream schemas would become an accidental public contract. Core migrations and
runtime logic would then need to understand source-specific vocabulary and version drift.

### Treat an external benchmark result as final security truth

Rejected because upstream scorers observe different endpoints and may combine task utility,
assistant text, tool intent, tool execution, and environmental effects differently. The project
must retain its own assertion and evidence semantics.

### Maintain one production runtime adapter per benchmark

Rejected because each adapter would be a shallow compatibility layer over a second execution
kernel. The apparent common interface would hide rather than remove incompatible environment,
trace, oracle, and cleanup semantics.

### Copy complete upstream environments into the repository

Rejected because it obscures provenance, imports broad dependency and license obligations, and
creates an unowned fork. Only explicitly approved assets or small implementations may cross the
boundary.

## Migration Strategy

1. Pin and audit each source repository, commit, relevant paths, software license, data terms, and
   restrictions in `references/manifest.yaml`.
2. Use `reference_only` until the source-level audit supports a more permissive mode. Unknown or
   mixed licenses block copying.
3. Run small importer spikes for representative sources. The spikes define minimum field
   candidates and loss reports; they do not freeze the complete domain model.
4. Compare selected imported cases with `upstream_replay` where practical. Differences must be
   explained as intentional normalization or treated as conversion failures.
5. Promote only self-contained, provenance-complete Scenario Packs to the project runtime.
6. Add dependency checks when importer and runtime packages exist so the prohibited edges become
   mechanically enforced.
7. Re-import deliberately from a newly audited commit. Never let a floating upstream dependency
   change a released Scenario Pack in place.

No production importer or runtime implementation is part of this ADR's documentation phase.
