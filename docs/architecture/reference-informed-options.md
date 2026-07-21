# Reference-Informed Architecture Options

- Status: candidate architecture for review
- Date: 2026-07-16
- Decision state: no package layout, class names, persistent schema, or formal API is frozen

This document compares implementation shapes within the already accepted product constraints. It
does not reopen those constraints:

- the Campaign Controller is the sole top-level controller;
- Inspect AI owns future Batch/Sample execution;
- PyRIT may own adaptive turns only inside one run;
- promptfoo supplies attack candidates only;
- only the project's final assertion process produces formal security truth;
- the target is a complete Agent system configuration; and
- security, attack progress, control outcome, and normal-task utility remain separate.

## Option A: Thin Core Around Inspect AI

Use Inspect `Sample`, `TaskState`, `Score`, and `EvalLog` as most execution and result objects. Keep
only Campaign selection, candidate import, final assertions, and artifact indexing project-owned.

| Dimension | Assessment |
| --- | --- |
| Implementation cost | Lowest; the execution spike proves the basic lifecycle. |
| Reuse | Highest immediate reuse of Inspect scheduling, tools, sandbox, scoring, and logs. |
| Third-party coupling | High; Inspect types would cross orchestration, assertion, and storage boundaries. |
| Upgrade risk | High because Inspect is beta and log/sample schemas evolve rapidly. |
| Testability | Good for execution tests; awkward for framework-independent assertion/storage tests. |
| Reproducibility | Adequate while complete Inspect logs and versions are retained. |
| Unique control/truth | Possible, but easy to erode if Inspect Scorers become de facto final results. |
| Internship fit | Fast first demo, costly to unwind if additional backends or durable artifacts arrive. |
| License | MIT-compatible as a dependency. |

`INFERENCE`: this option is useful as an experiment but makes an execution framework the implicit
long-term domain standard. It is not recommended as the target architecture.

## Option B: Full Project-Native Domain Core

Define complete native models for campaigns, targets, scenarios, candidates, runs, traces, evidence,
assertions, outcomes, findings, corpus entries, and storage before integrating any framework.

| Dimension | Assessment |
| --- | --- |
| Implementation cost | Highest; many contracts would be speculative. |
| Reuse | Lower initially because every third-party type is converted immediately. |
| Third-party coupling | Lowest. |
| Upgrade risk | Localized to integration boundaries. |
| Testability | High after the model stabilizes, but early tests validate assumptions rather than workflows. |
| Reproducibility | Potentially strongest if schemas and migrations are correct. |
| Unique control/truth | Explicit and easy to enforce. |
| Internship fit | Poor; it delays an executable slice and risks a large unused model. |
| License | Clean separation, with attribution isolated to integrations and importers. |

`INFERENCE`: this option has attractive long-term properties but violates the current evidence-first
phase. It is rejected for initial implementation, not rejected forever.

## Option C: Minimal Durable Core, Runtime-Local Third-Party Types

Keep third-party objects inside backend, policy, and importer boundaries. Define a project-owned
field or type only when the first vertical slice demonstrates that the value must cross at least two
boundaries or survive for replay. Persist raw upstream artifacts alongside a deliberately small,
versioned project summary.

Conceptual flow (labels are responsibilities, not proposed module or class names):

```text
Campaign ownership
  -> approved scenario + candidate + target configuration
  -> Inspect execution boundary
       -> target session and observed events
       -> optional per-run PyRIT policy
       -> raw Inspect/PyRIT artifacts
  -> trusted evidence collection
  -> final project assertion
  -> separately recorded security / progress / control / utility
  -> replay and regression artifacts
```

| Dimension | Assessment |
| --- | --- |
| Implementation cost | Moderate and incremental. |
| Reuse | High where upstream APIs fit; conversion is limited to durable/cross-boundary facts. |
| Third-party coupling | Contained inside explicit runtime/import boundaries. |
| Upgrade risk | Moderate; raw artifacts preserve forensic detail while contract tests catch integration drift. |
| Testability | High for one vertical slice without inventing the full future system. |
| Reproducibility | Strong if versions, target config, fixture, random seed, raw logs, and assertion inputs are retained. |
| Unique control/truth | Explicit: integrations return observations or progress, never a formal final verdict. |
| Internship fit | Best balance of executable progress and reversibility. |
| License | Clear dependency, integration, and importer ledgers; no source copying required. |

## Recommendation

Adopt Option C.

The first implementation should introduce only enough project-owned contract to cross this single
path:

```text
one versioned Coding/CLI case
  -> one target configuration
  -> one deterministic attack input
  -> one Inspect sample with a real isolated tool action
  -> one trusted environment observation
  -> one final assertion
  -> one replayable result with utility kept separate
```

Do not decide the final files or classes before that slice. During the slice, add a durable field
only when at least one of these conditions holds:

- it is shared across more than one backend/importer;
- it must be persisted for replay or regression;
- it expresses evidence provenance or trust that an upstream type cannot express;
- it protects the unique Campaign-control or final-truth boundary; or
- an upstream API/version/license is too unstable to become a durable contract.

Inspect `Sample` can therefore remain the execution carrier. Rights-approved static AgentDojo asset
records may appear as inputs to an Offline Benchmark Importer; executable AgentDojo `Task` objects
may appear only inside an isolated Upstream Replay Harness. PyRIT AttackContext remains inside its
per-Run policy integration. ClawSentry event and trajectory semantics are design references only;
its Gateway models and concrete adapters are not project import formats or standards. Promptfoo test
cases remain candidate-generation import formats, not project standards.

## Boundary Decisions Proposed Now

These are responsibility boundaries, not a requested directory tree:

| Boundary | Owns | Must not own |
| --- | --- | --- |
| Campaign | cross-run selection, budgets, stopping, retries, corpus feedback | tool execution internals or final assertion implementation |
| Inspect execution | sample concurrency, limits, sandbox lifecycle, raw execution log | campaign generations or formal final truth |
| Target/observation | all target calls and capability-aware event capture | attack selection or security verdict |
| PyRIT policy | next-turn choice and bounded per-run stop feedback | cross-sample concurrency, campaign state, final outcome |
| promptfoo generator | candidate generation and provenance | target execution, evaluation, or authoritative labels |
| Final assertion | complete trusted evidence and formal security result | attack mutation or framework lifecycle |
| Utility oracle | normal-task completion | security-result substitution |
| Artifact/replay | versioned inputs, raw logs, evidence, assertion inputs/results | reinterpretation of old results without schema/version tracking |

## Decisions Intentionally Deferred

- package/directory decomposition and final type names;
- database technology and normalized tables;
- whether the durable trace is one event schema or multiple evidence views;
- the complete outcome enum and metric catalog;
- target protocol choice beyond the first Coding/CLI Target Adapter;
- promptfoo Node sidecar versus long-lived process (CLI first);
- PyRIT worker/process isolation design;
- external dataset normalization schema; and
- the repository's formal license.

## Inspect Spike Result

- Hypothesis: one run identifier can survive through a Sample while a custom Solver,
  model-generated tool call, sandbox effect, custom Scorer, and EvalLog remain correlated.
- Location: `experiments/inspect-execution-model/`.
- Fixed runtime: Inspect AI `0.3.246`, tag commit
  `05322696a0f784ec399ef6abbafd3d2a250ea9cc`.
- Result: success; the custom `marker_solver` ran, `sample_id` and project run metadata matched, one
  tool message was logged, and the scorer observed the file side effect before sandbox cleanup.
- Additional fact: `EvalLog.samples` may be lazy, so required fields must be read while its backing
  log remains available.
- Limitations: mock model, local sandbox rather than Docker, one sample, no external Agent, no
  cancellation/retry test, and no claim that the Inspect Score is final truth.

Subsequent M0-B and M0-C validation pinned PyRIT `0.14.0` and exercised project-owned target/scorer
integration plus serialized in-process CentralMemory isolation. Remaining risks are the private
`PromptTarget._memory` compatibility check, PyRIT upgrades, and process/worker isolation for true
parallel policy execution; they do not reopen the bounded per-Run integration decision.

## Adversarial Boundary Check

- Red-team failure mode: a future integration persists an Inspect `Score` or PyRIT objective score as
  the security result, or lets a third-party executor schedule work across runs.
- Blue-team defense: keep those types and lifecycles inside integration boundaries, and require the
  first vertical slice to prove that the project assertion consumes trusted evidence independently.
- Residual risk: no production contract or architectural test enforces this yet. The recommendation
  remains provisional until the first vertical slice supplies that proof.
