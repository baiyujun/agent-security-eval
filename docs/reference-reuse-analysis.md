# Reference Reuse Analysis

- Audit date: 2026-07-16
- Status: research baseline for review
- Scope: repository facts, source-level extension boundaries, reuse classification, and license risk
- Non-goal: this document does not freeze package layout, module names, or a domain model

`FACT` is directly supported by a fixed repository revision, repository metadata, or a recorded
command result. `INFERENCE` interprets those facts for this project. `RECOMMENDATION` is a proposed
choice. `UNKNOWN` is deliberately unresolved.

## New Repository Inspection

The inspection baseline is `baiyujun/agent-security-eval@4d8c415d52b8c2339fc3bfc75a2ebb72640bf7b9`
before this research branch changed any files.

| Kind | Finding |
| --- | --- |
| FACT | The repository had one commit and one remote branch, `main`; the working tree was clean. |
| FACT | The source layout contained `.github/workflows`, `docs`, `references`, `src/agentsec_eval`, and `tests`; it did not contain product feature modules. |
| FACT | `pyproject.toml` uses Hatchling, package name `agent-security-eval`, import package `agentsec_eval`, and Python `>=3.11`. |
| FACT | Runtime dependencies were empty. The `dev` extra contained Ruff, MyPy, Pytest, and pytest-cov. |
| FACT | Ruff targets Python 3.11 with `E,F,I,B,UP`; MyPy is strict over `src` and `tests`; Pytest uses strict markers. |
| FACT | CI uses Python 3.11 and runs install, Ruff lint/format, MyPy, and Pytest. The initial `main` run succeeded. |
| FACT | Existing implementation was only `__version__ = "0.1.0"` plus one import smoke test. |
| FACT | README correctly said the project was not an intent classifier or production online guardrail and stated that no formal repository license had been selected. |
| FACT | `references/manifest.yaml` named eight projects but had `commit: null` for all of them and presented planned integration modes as if already selected. |
| FACT | Local branches observed during research were `main`, `research/reference-reuse-architecture`, and the auxiliary linked-worktree branch `codex/reference-audit`; all began at the baseline commit. Before this branch was delivered, the remote advertised `main` plus the auxiliary `codex/reference-audit` branch. |
| FACT | The baseline working tree was clean. This research branch changes documentation, the reference manifest, and one throwaway experiment; it does not change the package or product tests. |
| INFERENCE | The package and CI skeleton are sufficient for research work; adding feature directories now would create structure without evidence. |
| RECOMMENDATION | Keep the current package empty until one vertical execution-and-assertion milestone establishes the smallest persistent contracts. |
| UNKNOWN | The final repository license, artifact store, serialization format, and public API are not selected. |

### Visibility Correction

`FACT`: GitHub REST metadata initially reported the newly created repository as private. On
2026-07-16 it was changed to public. Verification returned `visibility=PUBLIC`, `isPrivate=false`,
and default branch `main`. An anonymous command with GitHub tokens unset, terminal prompting
disabled, an empty askpass, and `credential.helper=` returned:

```text
4d8c415d52b8c2339fc3bfc75a2ebb72640bf7b9  HEAD
4d8c415d52b8c2339fc3bfc75a2ebb72640bf7b9  refs/heads/main
```

## Legacy Audit Recovery

The legacy repository was read only. No commit was cherry-picked and no history or business code
was imported.

- Source repository: `baiyujun/intent-engine-legacy`
- Source branch: `audit/reference-baseline`
- Source commit: `558c28e75e9fb26a679b758bafba276f338a123c`
- Commit date: 2026-07-15
- Revalidation date: 2026-07-16

| File | Audited object and fixed revision | Status | Reason |
| --- | --- | --- | --- |
| `docs/references/CLAWSENTRY_SOURCE_AUDIT.md` | ClawSentry `b5fe3a764e10e78f7fd5799cb9438896cdb60096`, MIT | current facts; partially stale disposition | The upstream SHA is still current. Event and pattern evidence remains useful, but an online gateway is outside the locked product role. |
| `docs/references/PROMPTFOO_SOURCE_AUDIT.md` | promptfoo `fcde2e89a89dc4ca79dcc3012927f50193251759`, MIT | current facts; partially stale disposition | The upstream SHA is still current. Its claim that promptfoo should supply the principal outer loop conflicts with promptfoo's now-locked candidate-generation-only role. |
| `docs/references/PAPER_2605_01143_SOURCE_AUDIT.md` | arXiv v2 and code `acd51089d05cc13fcb29644170db764a94d936f6`, no code license found | requires separate revalidation | It is not one of the eight formal references for this task. Its no-license finding prevents code reuse. |
| `docs/references/REFERENCE_BASELINE.md` | promptfoo, ClawSentry, and the paper | partially stale and incomplete | It covers only three references, assigns promptfoo outer-loop ownership, and links to crosswalk/open-question files absent from the fixed commit. |

`RECOMMENDATION`: retain this provenance summary rather than copying the four legacy files. The new
analysis below supersedes their project-level adoption decisions.

## Fixed Reference Baseline

Repository activity dates are evidence of recent maintenance, not an API stability guarantee.

| Project | Official repository | Fixed commit | Stable release/tag at audit | Language / packaging | License | Maintenance / API assessment |
| --- | --- | --- | --- | --- | --- | --- |
| promptfoo | `promptfoo/promptfoo` | `fcde2e89a89dc4ca79dcc3012927f50193251759` | `0.121.19` | TypeScript; npm workspaces and lockfile | MIT | Active; CLI is the least-coupled boundary, but its selected release and output contract still require validation. |
| Inspect AI | `UKGovernmentBEIS/inspect_ai` | `ea007a79c556e30fb391c5e98ce2bf80b2362fbf` | tag `0.3.246` at `05322696a0f784ec399ef6abbafd3d2a250ea9cc`; no GitHub Release | Python; setuptools, pip/uv lock | MIT | Active beta with rapid tags; documented Python decorators/protocols are the intended extension boundary. |
| ClawSentry | `Elroyper/ClawSentry` | `b5fe3a764e10e78f7fd5799cb9438896cdb60096` | `v0.8.6` | Python; setuptools | MIT | Beta; audited HEAD is two commits and a very large tree change beyond the release. |
| PyRIT | `microsoft/PyRIT` | `339a28ff5e9873713006fc4f94637f595f9f9c59` | `v0.14.0` | Python; setuptools and uv lock | MIT | Active; HEAD declares `0.15.0.dev0`, so release and audited APIs must not be conflated. |
| AgentDojo | `ethz-spylab/agentdojo` | `089ed468cf3ed0322acc66b0211f26d9d90dbf60` | `v0.1.35` | Python; Hatchling and uv lock | MIT, with embedded third-party notices | Maintained, but HEAD is newer than the same-numbered package release. Suite/task APIs remain pre-1.0. |
| InjecAgent | `uiuc-kang-lab/InjecAgent` | `f19c9f2c79a41046eb13c03c51a24c567a8ffa07` | none | Python scripts and unpinned requirements | MIT at repository root | No commits since 2024-07; no package, tests, release, or stable API. |
| Agent Security Bench (ASB) | `agiresearch/ASB` | `1f561dccf92d55302368fa67679b4ba9d9c8fdc4` | none | Python scripts and partial requirements | MIT at repository root | Updated in 2026, but no package, tests, CI, release, or stable API. |
| WASP | `facebookresearch/wasp` | `ffee6f41fde76acd14bd792db442479c506260c2` | none | Python vendored applications; no root package | CC-BY-NC-4.0 root; MIT subdirectories | Archived; no stable API. Root code and data are commercial-use incompatible by default. |

All MIT projects permit internal and commercial use subject to preservation of copyright and
license notices when their source or substantial portions are distributed. That statement does not
resolve the provenance of every bundled dataset or every transitive dependency.

The fixed commit is the source-audit baseline; the release/tag column is repository metadata, not a
claim that the release contains identical code. Only the Inspect `0.3.246` subset described below
was executed at its release version. Every future dependency or CLI pin must be revalidated at the
exact installable version before adoption.

## Source-Level Findings

### Inspect AI

`FACT`:

- `src/inspect_ai/_eval/task/task.py::Task` composes Dataset/Sample, Solver or Agent, Scorer,
  sandbox, cleanup, limits, checkpointing, and metadata.
- `src/inspect_ai/dataset/_dataset.py::{Sample,Dataset}` supplies execution input, target,
  metadata, per-sample sandbox/files/setup, and a sequence abstraction.
- `src/inspect_ai/solver/_solver.py::{Solver,Generate}` and
  `src/inspect_ai/solver/_task_state.py::TaskState` retain the conversation and mutable state
  across multiple generations inside one sample.
- `src/inspect_ai/agent/_agent.py::{Agent,AgentState,agent}` and
  `src/inspect_ai/agent/_as_solver.py::as_solver` expose an Agent-to-Solver bridge.
- `src/inspect_ai/tool/_tool.py::{Tool,tool}` is the public tool extension point.
- `src/inspect_ai/util/_sandbox/environment.py::SandboxEnvironment` exposes exec/read/write and
  defines a per-sample filesystem context. `src/inspect_ai/_eval/task/sandbox.py::sandboxenv_context`
  initializes one sample environment, yields through solver and scoring, then cleans it up.
- `src/inspect_ai/scorer/_scorer.py::{Scorer,scorer}` is a public scoring extension point.
- `src/inspect_ai/log/_log.py::{EvalSample,EvalLog}` persists messages, output, scores, metadata,
  store, events, configuration, results, and format version. Samples may be lazily loaded from the
  log file.
- `examples/tool_use.py`, `examples/scorer.py`, `examples/bridge/agentsdk/task.py`,
  `tests/tools/test_sandbox_tool_eval.py`, and `tests/test_eval.py` exercise the above boundaries.
- The CLI entry is `inspect_ai._cli.main:main` under the `inspect` command.

`INFERENCE`: `Sample` is a good execution-time carrier but is too generic to be the durable security
contract. It has no stable semantics for evidence strength, harness integrity, final security truth,
attack progress, control outcome, and utility as separate dimensions.

`RECOMMENDATION`:

- Use released Inspect AI through its public API as the first execution dependency, behind a narrow
  backend boundary owned by this project.
- Convert one project-owned run description to one Inspect `Sample` inside that boundary. Keep
  `TaskState`, `Score`, `EvalSample`, and `EvalLog` out of persistent core interfaces.
- Use an Inspect Scorer to collect/transport project assertion output only. The project's final
  assertion process remains authoritative.
- Materialize required log fields before temporary log storage is removed.

`UNKNOWN`: Docker sandbox behavior, external Agent bridge behavior, concurrent artifact isolation,
and cancellation/retry semantics have not yet been exercised in this repository.

### PyRIT

`FACT`:

- `pyrit/executor/attack/core/attack_strategy.py::{AttackStrategy,AttackContext}` provides a
  per-attack lifecycle and context; `multi_turn/multi_turn_attack_strategy.py::ConversationSession`
  assigns fresh objective and adversarial conversation IDs per execution.
- `multi_turn/red_teaming.py::RedTeamingAttack._perform_async` loops until its objective scorer is
  true or `max_turns` is reached. Its constructor requires an objective scorer.
- `pyrit/prompt_target/common/prompt_target.py::PromptTarget.send_prompt_async` is final; custom
  targets override `_send_prompt_to_target_async` after normalization and capability validation.
- `pyrit/score/scorer.py::Scorer.score_async` is extensible and persists scores through central
  memory. A project-backed scorer can translate a progress assertion to PyRIT's stop signal.
- `pyrit/converter/converter.py::{Converter,ConverterResult}` is a public, modality-declaring
  extension boundary with extensive unit tests under `tests/unit/converter`.
- `pyrit/executor/attack/core/attack_executor.py::AttackExecutor` creates its own cross-objective
  concurrency loop.
- `pyrit/memory/central_memory.py::CentralMemory` holds one process-wide memory instance.
  `initialize_pyrit_async` replaces that singleton with one SQLite/in-memory/Azure SQL backend.
- Representative contract tests are
  `tests/unit/executor/attack/multi_turn/test_red_teaming.py`,
  `tests/unit/prompt_target/target/test_prompt_target.py`, and
  `tests/unit/memory/test_central_memory.py`. CLI entry points in `pyproject.toml` are
  `pyrit_backend`, `pyrit_scan`, and `pyrit_shell`; none is the proposed project integration boundary.

`INFERENCE`: the multi-turn strategy is reusable inside one run, but process-wide memory prevents a
claim of physical per-run memory isolation when multiple policies execute concurrently in the same
worker. Unique conversation IDs and labels provide logical separation only.

`RECOMMENDATION`:

- Use PyRIT only through an integration boundary that supplies a project-owned `PromptTarget` and objective
  scorer. Every target call must route through the same project Target/Observation boundary.
- Treat the adapted objective score as progress/stop feedback, never the final verdict.
- Do not call PyRIT `AttackExecutor` from the campaign path; the Campaign Controller and Inspect own
  cross-run scheduling.
- If selected after exact-release revalidation, reuse deterministic Converters through the installed
  PyRIT package inside the policy integration; do not copy them.
- Before enabling concurrent runs, test a worker-per-run design or prove that one shared memory with
  conversation/label filtering meets the isolation requirement.

`UNKNOWN`: the acceptable concurrency/isolation mechanism and exact v0.14 versus v0.15 API target.

### promptfoo

`FACT`:

- `src/main.ts` registers `promptfoo redteam generate` separately from `redteam run/eval/report`.
- `src/redteam/commands/generate.ts::{redteamGenerateCommand,doGenerateRedteam}` resolves plugins
  and strategies, invokes generation, and writes `redteam.yaml` (or a named YAML/Burp output)
  containing ordinary promptfoo test cases. Target evaluation is not required by this command.
- `src/redteam/index.ts::{synthesize,applyStrategies}` generates Plugin cases, applies Strategies,
  and returns test cases plus failure/token metadata. These are internal TypeScript functions, not a
  separately exported stable package contract.
- `src/redteam/plugins/base.ts::RedteamPluginBase.generateTests` uses a generation Provider and
  produces `{vars, assert, metadata}` test cases. Static/dataset plugins may disable remote
  generation.
- Deterministic strategies such as `strategies/{base64,rot13,leetspeak}.ts` transform cases locally.
  Adaptive strategy records such as Crescendo install provider wrappers; providers such as GOAT call
  the original Target during evaluation, so those records are not standalone attack candidates.
- `src/redteam/remoteGeneration.ts::shouldGenerateRemote` defaults to Promptfoo's remote endpoint
  when no local OpenAI/Codex credentials are usable. The disable environment variables force local
  mode, but then a suitable local generation provider is required. Some strategies explicitly
  require remote generation.
- Tests exist at `test/redteam/commands/generate.test.ts`, `test/redteam/index.test.ts`,
  `test/redteam/plugins/intent.test.ts`, and deterministic strategy test files.
- `doGenerateRedteamInternal` checks a local-database 100,000 monthly probe gate even for non-cloud
  users. When remote generation is not explicitly disabled, it also enters an email-validation
  flow. These are operational constraints on a supposedly local CLI boundary.

`INFERENCE`: the generation CLI is a usable process boundary and yields a parseable candidate
format. Importing internal TypeScript modules or running the full evaluator would add an unstable
API and duplicate control ownership.

`RECOMMENDATION`:

- Prefer a CLI integration that executes only `redteam generate` after revalidating an exact npm release,
  parses generated YAML with a schema, discards promptfoo assertions as non-authoritative, and
  records plugin/strategy provenance.
- Use an explicit allowlist of plugins and strategies whose output is a standalone candidate. Reject
  generated cases that install a provider wrapper or require target interaction; Crescendo, GOAT,
  and other adaptive evaluation strategies are outside this boundary.
- Default company runs to explicit local/self-hosted generation configuration. Do not silently send
  project purpose, tools, or targets to Promptfoo Cloud. Verify the email and probe-gate behavior in
  the selected release before treating the CLI as unattended or offline-capable.
- Defer a Node sidecar until repeated CLI startup or richer streaming proves it necessary.
- Do not source-copy simple strategies merely because they are small; implement project-native
  deterministic mutations only when a required invariant and tests are defined.

`UNKNOWN`: which plugins/strategies are approved for local-only company use and the exact stable
YAML subset that should become an import contract.

### ClawSentry

`FACT`:

- `src/clawsentry/gateway/models.py::CanonicalEvent` records event/trace/session/agent/framework,
  event type, tool and payload plus normalization metadata. The same file also contains extensive
  online policy, scope, rewrite, sanitize, and decision models.
- `adapters/codex_adapter.py::CodexAdapter` maps function/native hook events to PRE/POST actions.
  `adapters/gemini_adapter.py::GeminiAdapter` maps Gemini hooks and canonicalizes shell aliases.
  `cli/initializers/claude_code.py::ClaudeCodeInitializer` installs blocking and asynchronous hooks
  that invoke the ClawSentry harness.
- `gateway/analysis/post_action_analyzer.py::PostActionAnalyzer` examines tool output for
  instructional content, exfiltration strings, secret exposure, and obfuscation.
- `gateway/analysis/trajectory_analyzer.py::TrajectoryAnalyzer` implements five bounded ordered or
  count patterns: credential exfiltration, backdoor install, recon then exploit, secret harvest,
  and staged exfiltration.
- The package requires FastAPI/Uvicorn/Pydantic/PyYAML, and most adapters emit ClawSentry models or
  expect its gateway/harness lifecycle. Unit and integration tests live under
  `src/clawsentry/tests`.
- `pyproject.toml` exposes `clawsentry`, `clawsentry-gateway`, `clawsentry-harness`, and
  `clawsentry-stack` commands. Representative evidence tests are
  `test_codex_adapter.py`, `test_gemini_adapter.py`, `test_post_action_analyzer.py`, and
  `test_trajectory_analyzer.py` under `src/clawsentry/tests`.

`INFERENCE`: event vocabulary, capability honesty, and deterministic pattern semantics are useful;
the concrete models and adapters have strong gateway coupling and contain online verdict fields
that do not belong in an offline evaluation contract.

`RECOMMENDATION`:

- Use ClawSentry only as a design reference for cross-framework capability descriptions, unified
  events, and trajectory patterns. Project-owned Target Adapters may re-express those semantics but
  must not import or depend on ClawSentry's Gateway, online decision chain, domain models, or concrete
  framework adapters.
- Re-express validated trajectory rules as project assertions with explicit evidence requirements;
  do not carry risk weights or online `allow/block/modify/defer` outcomes into final truth.
- Do not import the complete Gateway or source-copy Codex/Gemini adapters in the first version; their
  dependency closure and enforcement semantics are larger than the needed observation mapping.

No ClawSentry package adoption is open for M1. Any future reconsideration requires a new fixed-source
audit and architecture decision.

### AgentDojo

`FACT`:

- `src/agentdojo/base_tasks.py::{BaseUserTask,BaseInjectionTask}` separates utility and injection
  security checks and supports trace-based checks with pre/post-environment fallback.
- `src/agentdojo/task_suite/task_suite.py::TaskSuite` owns environment/tool/task registries,
  version selection, YAML fixture injection, pipeline execution, and scoring.
- `TaskSuite.run_task_with_pipeline` loads and initializes an environment, deep-copies pre-state,
  runs its own Agent pipeline/runtime, then returns utility and injection-security booleans.
- Upstream `security=True` means the injection objective executed (attack success), not "the system
  is secure". This must be renamed on import.
- `src/agentdojo/default_suites/v1` supplies Python task classes and tools. YAML fixtures live under
  `src/agentdojo/data/suites/{workspace,travel,banking,slack}`.
- `functions_runtime.py::{FunctionsRuntime,Function,make_function}` derives tool schemas and mutates
  Pydantic environments. `GroundTruthPipeline` executes task ground truth.
- `src/agentdojo/yaml_loader.py::ImportLoader` contains embedded MIT and CC-BY-SA-attributed material
  and permits include paths that require a trust boundary.
- `pyproject.toml` declares no console script; `TaskSuite` is the Python entry boundary.
  Representative tests are `tests/test_benchmark.py`,
  `tests/test_functions_runtime/test_functions_runtime.py`, and
  `tests/test_workspace_user_tasks.py`.

`INFERENCE`: AgentDojo is valuable as an executable business-environment plugin, but its TaskSuite
runtime is not the project's general scenario model or Campaign Controller.

`RECOMMENDATION`: use an Offline Benchmark Importer for rights-approved static assets. If executable
comparison is required, provision the pinned dependency only inside an isolated Upstream Replay
Harness. Export no runtime objects; correct the attack-success polarity in project-owned Oracle
candidates. Treat Python suites and `!include` as trusted executable plugins, not untrusted data.
Workspace or travel can be a later vertical slice; Coding/CLI remains the first project milestone.

`UNKNOWN`: per-item data provenance and whether the root MIT license covers every bundled fixture.

### InjecAgent

`FACT`:

- Data comprises 17 user cases, 30 direct-harm attacker cases, and 32 data-stealing attacker cases.
  The base Cartesian sets contain 510 direct-harm and 544 data-stealing cases.
- `data/tools.json` contains 38 toolkits and 330 descriptive tools with parameter/return schemas,
  but no executable environment or side-effect oracle.
- `src/evaluate_prompted_agent.py` and `evaluate_finetuned_agent.py` build ReAct/tool-call histories;
  they are scripts rather than an installable framework.
- Data stealing is staged: S1 selects a data tool; a cached or GPT-generated simulated response is
  injected; S2 checks selection of `GmailSendEmail`. `src/utils.py::get_score` reports S1/S2 rates.
- `src/output_parsing.py` primarily checks target tool names, not argument correctness, actual tool
  execution, or environmental effects. The repository has no automated tests.

`INFERENCE`: these records are attack-seed and tool-schema inputs, not executable truth-labelled
scenarios. Several fields contain Python literals or nested encodings and require defensive parsing.

`RECOMMENDATION`: a read-only importer may preserve original JSON/JSONL and delay normalization.
Import the S1/S2 taxonomy as progress semantics, not final outcomes. Do not reuse the runner/parser
or invoke its GPT cache-filling path.

`UNKNOWN`: data provenance and whether top-level MIT fully covers model-generated/tool-description
content.

### Agent Security Bench

`FACT`:

- `scripts/agent_attack.py` expands YAML combinations and launches `main_attacker.py` through
  background shell commands. `main_attacker.py::main` creates a full benchmark controller with a
  very large thread pool.
- `pyopenagi/agents/react_agent_attack.py::ReactAgentAttack` implements direct prompt injection,
  observation injection, memory poisoning, and PoT backdoor behavior with five fixed templates.
  No generic Mutator class or mutation registry exists.
- `aios/` and `pyopenagi/` are vendored runtime code. `runtime/server.py` endpoints are placeholders.
- `check_attack_success` is a substring check over messages. Simulated attacker tools return the
  attack goal text, so the result is a tool-selection proxy, not an external-effect oracle.
- Data includes 400 attack-tool rows, 50 normal tasks, and 20 normal tools.
  `data/agent_task_pot_all.jsonl` is actually an access-restriction HTML page.
- There are no tests, package metadata, release, or complete dependency declaration.

`INFERENCE`: taxonomy and seeds are separable; the controller/runtime/evaluator are not trustworthy
execution or truth components for this project.

`RECOMMENDATION`: conditionally import validated JSONL rows with provenance and MIT attribution;
independently implement any required deterministic mutation. Reject the scripts, AIOS runtime,
Chroma memory binaries, simulated oracle, LLM refusal judge, and damaged data.

`UNKNOWN`: authorship/model-generation provenance of the JSONL assets.

### WASP

`FACT`:

- Root `LICENSE` is CC-BY-NC-4.0 and the repository is archived. Core
  `webarena_prompt_injections` code, prompts, and data are non-commercial by default.
- Independent MIT licenses exist under `visualwebarena`, `claude-35-computer-use-demo`, and
  `claude-37-computer-use-demo`; there is no independent Apache-2.0 subtree. Asset provenance still
  requires file-level review.
- `scripts/run_end_to_end.sh` owns setup, Agent execution, progress scoring, end-to-end attacker
  scoring, utility scoring, and cleanup: it is a competing top-level controller.
- `prompt_injector.py::WebArenaPromptInjector` inserts attacks into GitLab/Reddit state and creates
  separate benign-task and attacker-goal configs.
- `evaluator_step_by_step.py::ModelInferenceEngine` uses an LLM for compromised/refusal progress
  labels and defaults unparsable output to not compromised.
- `visualwebarena/evaluation_harness/evaluators.py::HTMLContentExactEvaluator` can inspect
  environment state. WASP's exfil evaluator also uses action-text substring evidence, which does
  not prove receipt by an attacker.
- The CC-BY-NC data contains 21 attacks and 37 utility tasks.
- The root prompt-injection application has no automated tests; tests found in the repository belong
  to independently licensed vendored VisualWebArena or Claude demo directories.

`INFERENCE`: the strongest reusable contribution is the separation of progress, end effect, and
utility, not the code, data, or lifecycle.

`RECOMMENDATION`: use WASP core only as `DESIGN_REFERENCE`. Do not copy or transform its code/data
for company or commercial use without legal approval or separate permission. Independently MIT
VisualWebArena material still requires a separate file and asset audit; any source runtime remains
limited to isolated upstream replay.

`UNKNOWN`: whether internal company research qualifies as non-commercial; treat it as incompatible
until legal counsel or the rights holder says otherwise.

## Inspect Release Spike Evidence

`FACT`: the throwaway command below ran against the released Inspect AI `0.3.246` package (tag commit
`05322696a0f784ec399ef6abbafd3d2a250ea9cc`), separately from the source-audit commit:

```bash
python experiments/inspect-execution-model/spike.py
```

```json
{"custom_solver":"marker_solver","inspect_ai":"0.3.246","log_status":"success","project_run_id":"inspect-spike-run-001","sample_id":"inspect-spike-run-001","score":"C","tool_messages":1}
```

The run correlated Sample metadata, a custom Solver, a model-generated tool call, a local-sandbox
file effect, a custom Scorer, and one EvalLog sample. `UNKNOWN`: Docker isolation, real model/Agent
bridges, multiple Samples, cancellation, retries, and concurrent artifact isolation remain untested.

## Reuse Decision Matrix

| Project | Fixed version | Candidate capability | Evidence location | Classification | License | Coupling risk | First-version decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Inspect AI | `0.3.246` / tag SHA above | Public Batch/Sample execution, tool, sandbox, and log APIs | release spike plus `Task`, `Sample`, `Solver`, `SandboxEnvironment`, `EvalLog` paths above | `DIRECT_DEPENDENCY` | MIT | Medium beta API churn | Candidate dependency after Docker and multi-sample contract validation. |
| Inspect AI | same | Project input/output conversion and log materialization lifecycle | lazy `EvalLog.samples` plus execution-boundary findings above | `ADAPTER_REUSE` | MIT | Medium type/lifecycle leakage | Keep Inspect types inside the execution boundary. |
| PyRIT | audit SHA; release target deferred | Per-run adaptive multi-turn policy | `RedTeamingAttack`, `PromptTarget`, `Scorer` | `ADAPTER_REUSE` | MIT | High: singleton memory and own executor | Defer production use until scorer/target and concurrency isolation spike. |
| PyRIT | same | Deterministic converters | `pyrit/converter` | `ADAPTER_REUSE` | MIT | Medium dependency closure/API target unresolved | Defer; if adopted, use only through the pinned package inside the policy boundary. |
| PyRIT | same | Cross-objective executor | `AttackExecutor` | `REJECT` | MIT | Duplicates campaign scheduling | Do not call from the campaign path. |
| promptfoo | audit SHA; release pin deferred | Standalone candidate generation | `redteam generate`, `doGenerateRedteam`, `synthesize` | `ADAPTER_REUSE` | MIT | Medium: Node, YAML, remote/email/probe behavior | Revalidate a release and use an explicit plugin/strategy allowlist. |
| promptfoo | same | Target-calling adaptive providers and evaluator | Crescendo/GOAT providers and `redteam run/eval` | `REJECT` | MIT | Duplicates Target execution and truth/control paths | Reject from the candidate-generation integration. |
| ClawSentry | audit SHA | Framework event-normalization semantics | event and trajectory vocabulary | `DESIGN_REFERENCE` | MIT | High gateway/model coupling | Re-express validated concepts only; do not consume ClawSentry event streams. |
| ClawSentry | audit SHA | Deterministic post/trajectory patterns | analyzer files above | `DESIGN_REFERENCE` | MIT | Medium assumptions/false positives | Re-express only validated rules as project assertions. |
| ClawSentry | audit SHA | Gateway, online policy models, concrete adapters | gateway/model/adapter files above | `REJECT` | MIT | High online-lifecycle coupling | Do not import or source-copy in the first version. |
| AgentDojo | audit SHA | Stateful suites, utility/security oracles | `TaskSuite`, base tasks, runtime | `DESIGN_REFERENCE` / `DATA_REUSE` candidate | MIT plus embedded notices | High executable plugin/runtime | Offline import after per-asset review; upstream runtime is replay-only. |
| AgentDojo | audit SHA | Fixtures/tasks/vectors | `default_suites/v1` and `data/suites` | `DATA_REUSE` | provenance unresolved | Medium | Hold until per-item provenance and polarity conversion review. |
| AgentDojo | audit SHA | General pipeline/runtime ownership | `run_task_with_pipeline` | `REJECT` | MIT plus embedded notices | Competing execution lifecycle | Do not use it as a production Campaign Backend. |
| InjecAgent | audit SHA | Injection seeds and descriptive tool schema | `data/*` | `DATA_REUSE` | root MIT; data provenance unresolved | Low runtime, medium data | Preserve raw records; normalize only approved fields; discard labels as truth. |
| InjecAgent | audit SHA | DH and S1/S2 progress semantics | case taxonomy and `get_score` | `DESIGN_REFERENCE` | MIT | Low | Do not promote tool-selection rates to final truth. |
| InjecAgent | audit SHA | Script runner, parser, GPT cache fill, labels | `src/evaluate_*`, `output_parsing.py`, `utils.py` | `REJECT` | MIT | High truth/runtime weakness | Do not execute or import as an evaluator. |
| ASB | audit SHA | DPI/OPI/Memory/PoT taxonomy | configs and `ReactAgentAttack` branches | `DESIGN_REFERENCE` | MIT | Low/medium semantic assumptions | Re-express independently; do not copy templates by default. |
| ASB | audit SHA | Validated attack/task/tool seed rows | JSONL files | `DATA_REUSE` | root MIT; provenance unresolved | Medium data quality | Hold pending provenance review and reject damaged rows. |
| ASB | audit SHA | Controller, AIOS runtime, labels, damaged asset | scripts, runtime, evaluators, PoT file | `REJECT` | MIT | Competing control and weak oracle | Do not import. |
| WASP | audit SHA | Threat model and three-way evaluation semantics | prompt-injection runner/evaluators | `DESIGN_REFERENCE` | CC-BY-NC-4.0 | Legal and runtime high | No code/data reuse. |
| WASP | audit SHA | Root core code/data and top-level runner | `webarena_prompt_injections` | `REJECT` | CC-BY-NC-4.0 | Commercial/legal and competing control | Do not copy or adapt without approval. |
| WASP vendored directories | audit SHA | VisualWebArena or Claude demo environment | independently licensed subdirectories | `REJECT` | MIT, asset caveats | High environment closure | Reconsider only after a separate file/asset audit. |

Each row above assigns one candidate capability exactly one classification. No `SOURCE_REUSE`
candidate is approved for the first version. Copying code would add attribution
and dependency-closure work without improving the currently needed boundary validation.

## Capability Matrix

| Project capability | Preferred source | Alternative | Project-owned part | Validation still required |
| --- | --- | --- | --- | --- |
| Batch/sample execution | Inspect AI | none selected | Campaign scheduling and run identity | Docker, cancellation, retries, artifact correlation |
| Sandbox | Inspect Docker/Compose | later project-owned Sandbox backend | Trust boundary and probe policy | Host/Agent isolation and cleanup |
| Target connection | project-owned Target Adapter over the Inspect Agent/Solver bridge | ClawSentry semantics only | Target capability contract and observation normalization | Black/gray-box capability matrix |
| Multi-turn attack | PyRIT adapted per run | project-native deterministic policy | budgets, control ownership, final verdict | CentralMemory concurrency isolation |
| Deterministic mutation | project-owned | PyRIT converters | seed lineage and reproducibility | required mutation set and invariants |
| Scenarios | first project-native Coding/CLI slice | AgentDojo later | scenario semantics, fixtures, reset | smallest vertical scenario contract |
| Attack seeds | promptfoo CLI, approved InjecAgent/ASB rows | PyRIT converters | provenance, approval, lineage | local generation and data rights |
| Trace normalization | project-owned | ClawSentry semantics | evidence source/strength and durable schema | actual target event formats |
| Environment oracle | project-owned Coding/CLI probe | offline-imported scenario semantics | trusted final state collection | tamper resistance and negative evidence |
| Task utility | project-owned scenario oracle | AgentDojo | separate utility result | same-fixture comparison |
| Final assertion | project-owned only | none | sole security truth | first deterministic assertions |
| Result storage | project-owned | raw Inspect logs as evidence attachment | durable separated result/artifact schema | minimal persisted fields and versioning |

## Adopt, Adapt, Build

`RECOMMENDATION`:

- Directly depend on: Inspect AI's released public execution APIs only after the remaining execution
  contract tests pass at an exact pinned release.
- Adapt: Inspect execution/log lifecycle, PyRIT per-run attack policy and any selected converters,
  promptfoo generation CLI, offline-imported AgentDojo fixture semantics, and validated ClawSentry
  event/trajectory concepts re-expressed in project vocabulary.
- Build: Campaign control, target capability/evidence contract, deterministic mutation needed by
  the first slice, normalized durable evidence, environment/task oracles, final assertion, separated
  result semantics, provenance, corpus feedback, and artifact/regression storage.
- Reject from first-version core: all third-party campaign/executor loops, all third-party final
  graders, ClawSentry Gateway enforcement, AgentDojo general runtime ownership, InjecAgent/ASB
  runners, and WASP core code/data.

## License Ledger

| Upstream | License evidence | Planned material / exact files | Modification/copy | Commercial use | Attribution / additional constraint |
| --- | --- | --- | --- | --- | --- |
| Inspect AI | root `LICENSE` at audit and release SHAs | installed public execution APIs; no repository files | none copied | permitted by MIT | Retain upstream copyright/license text where distribution requires it and record the dependency/version in the SBOM. |
| PyRIT | root `LICENSE` | optional installed policy and `pyrit/converter/**` APIs | none copied | permitted by MIT | Retain upstream copyright/license text where required; release/API target is unresolved. |
| promptfoo | root `LICENSE` | future pinned CLI plus generated YAML candidate import; no source path selected | no source copied | permitted by MIT | Retain package copyright/license text; record generated-output provenance and any service terms separately. |
| ClawSentry | root `LICENSE` | event/pattern semantics only; no files selected | none | permitted, but no material adopted | Cite repository and SHA in derived design/assertion records. |
| AgentDojo | root `LICENSE`; embedded notices in `src/agentdojo/yaml_loader.py` | possible offline-imported `src/agentdojo/data/suites/**` assets; no runtime | none in this PR | conditional on asset review | Preserve root MIT and applicable embedded MIT/CC-BY-SA attribution; approve fixture provenance before import. |
| InjecAgent | root `LICENCE` | possible `data/user_cases.jsonl`, `attacker_cases_dh.jsonl`, `attacker_cases_ds.jsonl`, and `tools.json` import | none in this PR | conditional on data provenance | Preserve repository/SHA and MIT notice; review model-generated and third-party content. |
| ASB | root `LICENSE` | possible validated rows from `data/all_attack_tools.jsonl`, `agent_task.jsonl`, and `all_normal_tools.jsonl` | none in this PR | conditional on data provenance | Preserve repository/SHA and MIT notice; reject `agent_task_pot_all.jsonl` and other corrupt/unprovenanced rows. |
| WASP | root `LICENSE`; separate `LICENSE` files under `visualwebarena` and both Claude demo directories | design semantics only; no files selected | none | core is not approved for commercial use | Do not copy code/data; any independent MIT subtree use needs a separate file and asset audit. |

Repository license status remains **not selected**. This audit does not grant a license to this new
repository.

## Open Questions

- Which exact Inspect AI version range should become the first runtime dependency?
- Can PyRIT memory be isolated safely under concurrent Inspect samples without a process per run?
- Which promptfoo plugins and strategies are permitted and reproducible in local/self-hosted mode?
- What minimum target observation capability is required for the first Coding/CLI scenario?
- Which external datasets pass per-item provenance and commercial-use review?
- What is the smallest durable artifact needed to replay one assertion-backed finding?
