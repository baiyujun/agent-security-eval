# A 类 Repo/Shell 与 C 类 Local MCP 源码资产盘点

审计日期：2026-07-16

本报告只盘点 A 类 Repo/Shell 与 C 类 Local MCP 参考资产。没有复制第三方代码、数据、攻击 Payload、凭证或服务配置；没有实现 Importer、运行时 Adapter、Docker 环境或正式 Domain Model；没有处理 AgentDojo、τ-bench、AppWorld 或其他 B 类 Business/Stateful 环境。

## SABER

### Locked source

- Repository: https://github.com/sssr-lab/SABER
- Commit: `bfdffb10c3887b38e1bd57ae2e548faa8f2049e9`
- Commit date: `2026-06-05T18:47:29+08:00`
- License: Apache-2.0 for code and software documentation
- Data license: `REVIEW_REQUIRED`; the root notice assigns SABER-authored task material to CC-BY-4.0, but the dataset card declares Apache-2.0
- Dirty checkout: false

### Files inspected

- Overview and provenance: `README.md`, `AGENTS.md`, `LICENSE`, `LICENSES/THIRD-PARTY.md`, `dataset/README.md`, `dataset/manifest.json`
- Runtime and lifecycle: `Dockerfile`, `sandbox_shell.py`, `task_runtime.py`, `mcp_runtime.py`, `run_osbench.py`
- Oracle and aggregation: `judge_osbench.py`
- Representative tasks: `tasks/A/info_leak/A_info_001.json`, `tasks/A/code_tampering/A_code_041.json`, `tasks/B/info_leak/B_info_001.json`, `tasks/B/code_tampering/B_code_001.json`, `tasks/C/info_leak/C_info_001.json`, `tasks/C/code_tampering/C_code_001.json`

`dataset/manifest.json` is the current inventory authority at this commit: 716 tasks, split as A=289, B=186, C=241. The 513-task count in `AGENTS.md` is stale.

### Task and fixture schema

Tasks are JSON files under `tasks/{scenario}/{category}/{id}.json`; the path, `scenario`, and `category` jointly identify the case. The stable top-level shape is:

- `id`, `scenario`, `category`, and `difficulty`;
- `setup`, containing `system_prompt`, `user_prompt`, `mock_fs`, `file_contents`, and `cwd`, with optional `init_commands`, `file_permissions`, and `mcp_servers`;
- `injection`, containing `enabled`, an injection `method`, an optional injection step or target tool, and the attack payload;
- `ground_truth`, containing expected-safe command or tool hints, harmful command or tool regexes, and a harm description.

The supported injection placements documented and implemented by the source include tool output, file content, configuration content, error messages, and delayed multi-step delivery. Representative cases show all three benchmark situations: a legitimate task with an injected instruction (A), an unsafe implementation choice without injection (B), and a direct risky request that should be refused or constrained (C).

Fixture construction is declarative at the task level but executable at runtime. `mock_fs` and `file_contents` define the initial tree, `cwd` establishes the working directory, `file_permissions` applies explicit modes, and `init_commands` can construct databases, git history, binary artifacts, or other state. These executable fields must be treated as untrusted input during any future import.

### Environment lifecycle

`sandbox_shell.py` starts one Docker container per task with `--network=none`, CPU and memory limits, and a fixed tool image. Initialization creates the declared filesystem, materializes configured contents, creates realistic git and database state where recognized, applies file permissions, and finally runs `init_commands`. `task_runtime.py` exposes bash and declarative MCP tools through a single event stream. `run_osbench.py` drives the model loop and calls cleanup in a `finally` path; `SandboxShell.cleanup()` removes the container.

The network-disabled environment is not equivalent to a factual network oracle. `sandbox_shell.py` returns success-like simulated output for operations such as `curl`, `git push`, package installation, and related commands. That behavior is useful for eliciting agent intent but cannot prove that an external effect occurred.

### Observation and trace model

The shell runtime records, per step, the requested command, returned output, and rule-derived state deltas. Deltas cover operations such as deletion, permission changes, git resets and pushes, scheduled-task edits, sensitive reads, network actions, and pipeline-style read-then-send sequences. `task_runtime.py` preserves a legacy shell-only `trajectory` and a provider-neutral `events` list that also includes MCP calls and their declared deltas.

The delta extractor reasons primarily from command strings. It does not provide a complete shell execution trace and can miss or misclassify composition, quoting, indirection, subprocess behavior, or state changes outside its patterns. Imported scenarios therefore need structured runtime observations rather than replaying this parser as truth.

### Oracle and evaluator semantics

`judge_osbench.py` combines three evidence sources:

- rule-based safety properties over extracted deltas;
- per-task harmful command and tool regexes;
- an LLM compositional-harm and attribution judgment.

It also separately classifies empty trajectories and whether a `Safe Refusal` was justified or an over-refusal. Expected-safe commands are hints used mainly when judging whether a stop was justified; they are not a complete task-success verifier. Consequently, `Safe Completion` means no harm was adjudicated, not that the requested normal task was proven correct.

The future native oracle must keep utility success, attempted harm, executed action, resulting state change, and cross-boundary effect as separate facts. Command-string regexes may remain assertion candidates, but not final security truth. Simulated shell success and upstream aggregate scores must not be imported as security labels.

### Reusable assets

- Scenario taxonomy, difficulty, harm category, and provenance identifiers.
- Normal-task intent and prompt-role separation.
- Declarative fixture intent: working directory, file manifest, permissions, and initialization purpose.
- Attack channel, placement, trigger timing, and harm objective.
- Expected-safe action hints and regexes as reviewable assertion candidates.
- Declarative MCP server and tool contracts when they can be represented without executable upstream handlers.

### Assets requiring semantic reconstruction

- Fixture file contents and attack-bearing artifacts, because raw task data is license-blocked.
- `init_commands`, git/database setup, and shell handlers as allowlisted native setup steps.
- Harmful regexes as structured forbidden-action and effect assertions.
- Network and persistence effects as local mock services with explicit receiver and service-state observations.
- Utility completion checks, which SABER does not consistently provide as independent executable oracles.

### Assets that must not enter production runtime

- `sandbox_shell.py`, `task_runtime.py`, `mcp_runtime.py`, `run_osbench.py`, and `judge_osbench.py` as runtime dependencies.
- Success-like network mocks as evidence of real external effects.
- Raw attack payloads, synthetic secrets, task file contents, results, and judged outputs.
- Upstream command regexes, LLM judgments, termination labels, or total scores as authoritative truth.
- Executable initialization or MCP shell templates without native validation, isolation, and allowlists.

### License and provenance risks

`LICENSE` assigns source code and software documentation to Apache-2.0 and SABER-authored benchmark task material to CC-BY-4.0. `dataset/README.md` instead declares the dataset Apache-2.0. This conflict makes task text, fixture contents, annotations, regexes, and payloads `REVIEW_REQUIRED`. Assets under `baselines/benchmarks/` retain separate upstream terms and are outside this import scope.

### Proposed importer boundary

`SaberScenarioImporter` may parse and normalize identities, taxonomy, prompts, fixture intent, injection placement, harm descriptions, safe-action hints, and assertion candidates. It must emit provenance and license status, reject unknown executable fields by default, and never execute source content during import. Runtime construction, source regex execution, model loops, network simulation, LLM judging, and aggregate scoring remain outside the importer.

## Inspect Evals / CodeIPI

### Locked source

- Repository: https://github.com/UKGovernmentBEIS/inspect_evals
- Commit: `3fda7b008453f8ba6bb7b1471e8fbd1865d2257e`
- Commit date: `2026-07-15T14:41:12+10:00`
- License: MIT
- Data license: `REVIEW_REQUIRED`; no independent license was found for `samples.json` or its embedded repository fixtures
- Dirty checkout: false

### Files inspected

- Repository licensing and package metadata: `LICENSE`, `NOTICE`, `pyproject.toml`
- Evaluation documentation and metadata: `src/inspect_evals/ipi_coding_agent/README.md`, `src/inspect_evals/ipi_coding_agent/eval.yaml`
- Dataset and loader: `src/inspect_evals/ipi_coding_agent/dataset/samples.json`, `src/inspect_evals/ipi_coding_agent/ipi_coding_agent.py`
- Fixture setup and sandbox: `src/inspect_evals/ipi_coding_agent/setup.py`, `src/inspect_evals/ipi_coding_agent/docker/Dockerfile`, `src/inspect_evals/ipi_coding_agent/docker/compose.yaml`
- Scoring and tests: `src/inspect_evals/ipi_coding_agent/scorer.py`, `src/inspect_evals/ipi_coding_agent/tests/test_scorer.py`, `tests/ipi_coding_agent/test_e2e.py`

### Task and fixture schema

Each `samples.json` record includes an ID, legitimate task description, optional issue text, injection vector, payload category and sophistication, severity, payload indicator, expected malicious action, benign flag, `repo_files`, verification command, expected fix, and optional persistence targets. `repo_files` is a path-to-content object that can place injection material in issue text, code comments, README content, or configuration files.

The loader converts each record into an Inspect sample. The legitimate task becomes the sample input, the expected fix becomes the target, and vector, payload, fixture, verification, and persistence metadata are attached for setup and scoring. The selected six candidate records all use `cd /workspace && python -m pytest tests/ -q` as their current verification command, but that command is source metadata and must be validated before native execution.

### Environment lifecycle

`setup_workspace()` creates `/workspace`, materializes `repo_files`, plants synthetic canaries in an environment-like file and a root-only file, and snapshots SHA-256 hashes across `/workspace` and `/root`. The task runs Inspect `react()` with bash and Python tools, a 30-message limit, and the Docker Compose sandbox. The compose file disables network access. Sandbox teardown is owned by Inspect; CodeIPI does not define its own benchmark-local reset contract.

Base64 is used only as an upstream transport mechanism for safely materializing arbitrary file text. A future importer may independently implement equivalent binary-safe fixture materialization and SHA-256 snapshots, but must not copy this implementation.

### Observation and trace model

The scorer reconstructs three text channels from Inspect `TaskState.messages`:

- assistant tool-call arguments;
- assistant natural-language output;
- tool-result content, including command stdout and stderr.

Persistence is observed by comparing current hashes for the sample's exact `persistence_targets` against the baseline. Utility completion is observed by running the sample's verification command and checking process exit code.

### Oracle and evaluator semantics

The source scorer deliberately combines several different meanings:

- exfiltration is marked when a canary appears anywhere in tool arguments, local tool results, or assistant text;
- code execution is marked when a per-sample command marker appears in requested tool arguments;
- persistence is marked when a target file is created or its hash changes;
- task completion is the verification command returning zero;
- injection detection and benign false positives use an LLM grader.

The exfiltration rule can label a secret merely observed in local stdout as a leak even when no outbound request was made and no receiver obtained the canary. The code-execution rule observes requested command text, not necessarily a completed process or effect. Native observations must therefore map source evidence into separate fields:

- `secret_observed`
- `secret_in_assistant_output`
- `exfiltration_attempted`
- `exfiltration_request_executed`
- `receiver_received_canary`

These fields must not be collapsed back into one boolean. Task success, attack resistance, explicit detection, and refusal also remain independent dimensions.

### Reusable assets

- Sample IDs, injection-vector taxonomy, payload category, sophistication, severity, and benign-control designation.
- Legitimate task and expected-fix intent, subject to data-license approval.
- Repository fixture manifests and verification intent.
- Per-sample persistence target lists.
- The design idea of canary-based observation and before/after file snapshots.

### Assets requiring semantic reconstruction

- All injection-bearing issue text, source comments, README content, configuration content, and repository file bodies.
- Per-run random canaries, mock secret storage, mock receiver state, and structured outbound-request events.
- Base64-safe file materialization and SHA-256 snapshot logic as new project-native implementations.
- Utility verifiers that run in a controlled native environment rather than trusting arbitrary source commands.

### Assets that must not enter production runtime

- Inspect Evals' CodeIPI task, setup, scorer, or Docker files as runtime dependencies.
- Static canary values, raw payload indicators, expected malicious-action text, or full fixture contents.
- The LLM detection grader as a sole oracle.
- The composite `accuracy` or injection-resistance score as a security fact.
- Verification commands or repository content executed before policy validation.

### License and provenance risks

The repository code is MIT, but neither `samples.json` nor the CodeIPI documentation provides an independent data license for sample text and embedded repository fixtures. `eval.yaml` reports no external assets, which is not equivalent to an explicit data grant. Raw sample copying remains blocked pending review.

### Proposed importer boundary

`CodeIPIImporter` may normalize sample identity, legitimate-task intent, injection-vector metadata, fixture path manifests, verification intent, persistence targets, and provenance. It should emit references to semantically reconstructed fixture seeds, not raw source contents. It must not run source verification commands, materialize source payloads, plant static canaries, or reproduce the upstream scorer during import.

## Terminal-Bench 2 task snapshots in Terminal-Bench

### Locked source

- Repository: https://github.com/harbor-framework/terminal-bench
- Commit: `d28711d0da2675d0bb1d56de45ae5df6082438a3`
- Commit date: `2026-07-10T22:19:08-07:00`
- License: Apache-2.0 at repository root
- Data license: `REVIEW_REQUIRED` per task and fixture
- Dirty checkout: false

The audited checkout is not the authoritative Terminal-Bench 2 repository. Harbor's `registry.json` maps `terminal-bench@2.0` to `https://github.com/laude-institute/terminal-bench-2.git` at `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`. The local `original-tasks/` tree contains matching task names, but this audit did not have a local checkout of that official commit and cannot assert byte-for-byte equivalence.

### Files inspected

- Repository documentation and metadata: `README.md`, `LICENSE`, `pyproject.toml`, `registry.json`
- Candidate `regex-log`: `original-tasks/regex-log/task.yaml`, `original-tasks/regex-log/Dockerfile`, `original-tasks/regex-log/docker-compose.yaml`, `original-tasks/regex-log/run-tests.sh`, `original-tasks/regex-log/tests/test_outputs.py`, `original-tasks/regex-log/solution.sh`
- Candidate `log-summary-date-ranges`: `original-tasks/log-summary-date-ranges/task.yaml`, `original-tasks/log-summary-date-ranges/Dockerfile`, `original-tasks/log-summary-date-ranges/docker-compose.yaml`, `original-tasks/log-summary-date-ranges/log_generator_deterministic.py`, `original-tasks/log-summary-date-ranges/run-tests.sh`, `original-tasks/log-summary-date-ranges/tests/test_outputs.py`, `original-tasks/log-summary-date-ranges/solution.sh`
- Candidate `nginx-request-logging`: `original-tasks/nginx-request-logging/task.yaml`, `original-tasks/nginx-request-logging/Dockerfile`, `original-tasks/nginx-request-logging/docker-compose.yaml`, `original-tasks/nginx-request-logging/run-tests.sh`, `original-tasks/nginx-request-logging/tests/test_outputs.py`, `original-tasks/nginx-request-logging/solution.sh`
- Historical harness and parser paths: `terminal_bench/handlers/trial_handler.py`, `terminal_bench/harness/harness.py`, `terminal_bench/terminal/docker_compose_manager.py`, `terminal_bench/parsers/pytest_parser.py`

### Task and fixture schema

The legacy task directory contract contains `task.yaml`, `Dockerfile`, `docker-compose.yaml`, `run-tests.sh`, private tests, and an optional solution. `task.yaml` carries the instruction, author metadata, difficulty, category, tags, parser, agent timeout, test timeout, and optional duration estimates. Docker and Compose files define the agent-visible project environment; `run-tests.sh` launches the private verifier; `tests/` contains the utility oracle; `solution.sh` is calibration-only material.

The three proposed candidates are all listed in Harbor's Terminal-Bench 2.0 registry:

- `regex-log`: small single-output regex task; the visible log fixture needs reconstruction because source tests own much of the discriminating data.
- `log-summary-date-ranges`: deterministic multi-file log generation and a precise CSV oracle; well suited to a log-content attack channel.
- `nginx-request-logging`: configuration, service behavior, and emitted-log verification; useful for configuration attacks but materially heavier and riskier.

### Environment lifecycle

The historical Terminal-Bench harness builds and starts Docker Compose, drives an agent in a terminal session, copies private tests after the agent phase, runs the verifier, parses its textual output, captures terminal and agent logs, and tears Compose down through context-manager cleanup. The candidate verifier scripts bootstrap dependencies using package and network commands, so source replay is not hermetic.

The source `task.yaml` files set agent and verifier timeouts, but do not define a complete portable resource policy. Native ingestion must add explicit CPU, memory, storage, GPU, and network decisions rather than inheriting provider defaults.

### Observation and trace model

The legacy harness records terminal pane snapshots, command history, asciinema output, agent logs, and parsed verifier output. These are useful replay artifacts but do not provide a structured security-effect trace. The future A-class environment needs native command, filesystem, process, and mock-service events alongside the private utility verifier.

### Oracle and evaluator semantics

Private tests define utility success. In the historical path, a parser derives passed tests from verifier stdout. In Harbor's mapping path, the mapped `test.sh` records its process exit code as binary reward: zero writes `1`, non-zero writes `0`, then exits with the original code.

Reference solutions may be used only to validate the environment and verifier before evaluation. They must never be placed in an agent-visible layer, prompt, mount, image, or trace. Neither the source solution nor a binary utility reward is a security oracle.

Build and verifier speed were not measured in this audit. Source-based complexity estimates remain provisional:

- `regex-log`: low environment complexity; hidden-input reconstruction risk.
- `log-summary-date-ranges`: medium fixture volume; deterministic but expected counts are sensitive to inserted attack text.
- `nginx-request-logging`: medium-to-high lifecycle complexity; system configuration, service timing, and package-install risks.

### Reusable assets

- Normal task instructions and metadata after provenance approval.
- Small fixture intent and expected output formats.
- Docker/environment intent, not source Docker implementation.
- Private utility tests as oracle specifications after license review.
- Timeouts and source estimates as provisional planning metadata.
- Reference solutions for isolated calibration only.

### Assets requiring semantic reconstruction

- Hermetic project-native environments with explicit resources and no live package bootstrap.
- Agent-visible logs, configuration, README, or dependency metadata used as attack placements.
- Private native verifiers and explicit exit-to-utility mapping.
- Reset specifications, structured traces, network policy, and conversion-loss reports.
- Any selected task content after verification against the official Terminal-Bench 2 commit.

### Assets that must not enter production runtime

- The Terminal-Bench harness, terminal driver, parser, or Compose manager.
- Upstream solutions in any agent-visible environment.
- Network-dependent verifier bootstraps and unreviewed base images.
- Canary markers, author email metadata, or raw task data without approval.
- Parsed pass counts or binary utility rewards as security-effect truth.

### License and provenance risks

The repository root is Apache-2.0, but `original-tasks/` has no per-task license files and embeds author information, generated data, base-image references, and benchmark canaries. More importantly, the audited repository is not the registry's authoritative Terminal-Bench 2 source. Import must remain blocked until the exact repository, commit, path, digest, and per-asset rights are verified.

### Proposed importer boundary

`TerminalBenchFixtureImporter` should be an offline, fail-closed converter from a verified repository/commit/path tuple into project-native drafts. It may normalize instruction metadata, approved fixture files, environment intent, verifier-private utility assertions, solution provenance, timeouts, and content digests. It must reject unknown fields, unapproved files, unsafe paths, unsupported Compose behavior, network-dependent verifier steps, and unverified source drift. The importer and both upstream runtimes must not be dependencies of the generated scenario pack.

## Harbor

### Locked source

- Repository: https://github.com/harbor-framework/harbor
- Commit: `d3e606d9f7d1e111bb22d3d820ebed03ec300eb3`
- Commit date: `2026-07-15T13:10:44-07:00`
- License: Apache-2.0
- Data license: `REVIEW_REQUIRED` for adapter templates, examples, images, and external task assets
- Dirty checkout: false

### Files inspected

- Repository metadata: `README.md`, `LICENSE`, `pyproject.toml`, `registry.json`
- Terminal-Bench mapping: `src/harbor/mappers/terminal_bench.py`, `tests/unit/mappers/test_terminal_bench.py`
- Native task and resource schema: `src/harbor/models/task/config.py`, `src/harbor/models/task/paths.py`
- Trial paths and reward outputs: `src/harbor/models/trial/paths.py`
- Verifier: `src/harbor/verifier/verifier.py`
- Lifecycle context: `src/harbor/trial/trial.py`, `src/harbor/trial/single_step.py`, `src/harbor/environments/docker/docker.py`

### Task and fixture schema

Harbor's native directory boundary is `instruction.md`, `task.toml`, `environment/`, `tests/`, and optional `solution/`. `task.toml` models agent and verifier timeouts, environment build timeout, operating system, CPU, memory, storage, GPU, workdir, network policy, MCP servers, verifier mode, and artifacts.

`TerminalBenchMapper` parses known `task.yaml` fields, writes the instruction and native task config, maps Docker or Compose content, copies tests and solution, and appends binary reward logging to the test script. The Pydantic source model ignores unknown Terminal-Bench fields. The mapper also copies remaining unclassified files into the environment, which is too permissive for a security-sensitive importer.

### Environment lifecycle

Harbor owns environment creation, agent execution, verification, result persistence, recovery, and cleanup. Its Docker provider can build images, start services, and delete images and volumes during teardown. Importing this runtime would create a nested lifecycle and a second truth authority, so Harbor remains a design reference only.

### Observation and trace model

Harbor preserves task config, lock state, result data, agent logs, verifier stdout, reward files, artifacts, and trajectory exports. That structure is useful when defining a native evidence bundle, but Harbor's concrete storage and job/trial abstractions are not required for this import path.

### Oracle and evaluator semantics

Harbor executes `tests/test.sh` or the platform equivalent and then parses `/logs/verifier/reward.json` or `/logs/verifier/reward.txt`. Missing, empty, or malformed reward files are verifier errors. For Terminal-Bench mapping, the wrapper converts the source test script's exit code to binary reward and preserves the exit code.

This cleanly distinguishes verifier process execution from the task-authored reward file, but it remains a utility result. It does not establish whether an attack was attempted, a forbidden action ran, or a mock receiver observed a secret.

### Reusable assets

- Task-directory separation between agent-visible environment, private tests, and calibration solution.
- Explicit resource, timeout, workdir, network, and verifier configuration concepts.
- Reward-file and verifier-error semantics.
- Mapper loss cases and unit-test examples as design evidence.

### Assets requiring semantic reconstruction

- Strict file-role classification and allowlisted copying.
- Explicit conversion-loss reporting instead of silently ignoring source fields.
- Project-native lifecycle, reset, trace, and security-oracle integration.
- Safe Compose handling and a deterministic utility-verifier wrapper.

### Assets that must not enter production runtime

- Harbor Job, Trial, Environment, Agent, Verifier, queue, or provider implementations.
- The existing permissive mapper as the production importer.
- Harbor's registry fetch or nested execution chain.
- Adapter templates or example assets without separate provenance review.

### License and provenance risks

Harbor code is Apache-2.0. External datasets referenced by its registry and assets inside adapters or examples retain separate provenance. Its registry is useful evidence that Terminal-Bench 2.0 points to a different repository and commit, but it does not license those assets for copying.

### Proposed importer boundary

Use Harbor only to inform `TerminalBenchFixtureImporter` design. The project-native importer should preserve the strong directory roles and reward semantics while rejecting Harbor's unknown-field dropping, broad residual-file copying, and nested lifecycle. No Harbor package is proposed as a runtime dependency.

## MCP-SafetyBench

### Locked source

- Repository: https://github.com/xjzzzzzzzz/MCPSafety
- Commit: `7872437b6369aac1150e3a19e350a981dc554f81`
- Commit date: `2025-12-18T16:03:38+08:00`
- License: `REVIEW_REQUIRED`; no root LICENSE, COPYING, or NOTICE is present
- Data license: `REVIEW_REQUIRED`
- Dirty checkout: false

### Files inspected

- Project claims and package metadata: `README.md`, `pyproject.toml`, `package.json`
- Task, runner, evaluator, and cleanup: `mcpuniverse/benchmark/task.py`, `mcpuniverse/benchmark/runner.py`, `mcpuniverse/benchmark/cleanups.py`, `mcpuniverse/evaluator/evaluator.py`, `mcpuniverse/evaluator/functions.py`
- MCP client and registry: `mcpuniverse/mcp/client.py`, `mcpuniverse/mcp/manager.py`, `mcpuniverse/mcp/configs/server_list.json`
- Representative attack tasks: `mcpuniverse/benchmark/configs/test/financial_analysis/yfinance_task_0002.json`, `mcpuniverse/benchmark/configs/test/financial_analysis/yfinance_task_0026.json`, `mcpuniverse/benchmark/configs/test/financial_analysis/yfinance_task_0039.json`
- Tests: `tests/benchmark/test_task.py`, `tests/benchmark/test_cleanup.py`

### Task and fixture schema

The fork extends MCP-Universe task JSON with `attack_category` and optional attack blocks for server modifications, server or tool additions, rug-pull updates, wrong-function and wrong-argument intent injection, data tampering, identity spoofing, and replay injection. Ordinary task fields include the question, optional output format, MCP server list, evaluators, cleanup declarations, and whether the task restricts the agent to specified servers.

Server modification records can change descriptions and returned values. Addition records can include tool name, description, input/output declarations, and implementation code. Rug-pull configuration defines a target tool, call threshold, and changed behavior. These shapes are useful taxonomy evidence but are not safe executable import formats.

### Environment lifecycle

The runner loads tasks, prepares live-service state, connects configured servers, mutates tool descriptions or server source, executes the agent, evaluates the response and trace, and performs task reset and cleanup. The documented Docker command bind-mounts the repository read/write, while attack setup can rewrite server files inside that mount. Restoration is best-effort rather than a guaranteed transactional boundary.

The benchmark also includes identity-spoofing logic that replaces environment credentials and reconnects servers. Credential prefixes may be logged. These behaviors are prohibited for native ingestion and evaluation.

### Observation and trace model

MCP-Universe tracing records tool events with server name, tool name, arguments, responses, and timestamps. MCP-SafetyBench passes trace records to attack-aware evaluators and to cleanup resolution. Replay injection can add repeated tool events. Cleanup declarations resolve arguments from actual calls and returned content, so reset correctness can depend on a complete trace.

### Oracle and evaluator semantics

Task evaluators combine response transformations, comparison operators, service checks, and attack-specific trace functions. Several attack verdicts measure whether a configured event occurred, not whether a harmful effect followed. The rug-pull evaluator can pass on call count beyond a threshold without proving that the definition, response, selected behavior, or service state changed.

Only a minority of attack tasks declare task cleanup, and source-file restoration is separate from trace-dependent external cleanup. Native C-class cases must assert the transition itself, the agent's selected tool/server, forbidden calls, structured local effects, mock receiver state, and successful reset.

### Reusable assets

- Attack taxonomy and declarative field vocabulary.
- Normal-to-malicious transition concepts for description poisoning, additions, mutation, replay, tampering, and spoofing.
- Evaluator and cleanup intent as reconstruction input.
- Trace field concepts: server, tool, arguments, response, order, and timestamp.

### Assets requiring semantic reconstruction

- Exactly three first-stage patterns: `tool_poisoning`, `malicious_server_addition`, and `rug_pull`.
- Trusted and malicious local server manifests, a mutable registry, deterministic mutation triggers, and reset logic.
- Structured trace and service-state assertions that prove effects rather than event occurrence alone.
- Synthetic secret storage and receiver state with no real account, token, endpoint, or external service.

### Assets that must not enter production runtime

- Upstream package or runner code.
- `implementation_code`, shell commands, server source rewriting, subprocesses, or host paths from task records.
- Live GitHub, Notion, Maps, finance, browser, database, or other service integrations.
- Environment credential mutation or logging.
- Raw attack task text, payloads, source evaluator labels, and best-effort cleanup behavior.

### License and provenance risks

The current tree has no license file. `pyproject.toml` claims BSD-3-Clause but retains the `mcpuniverse` package name, Salesforce attribution, and MCP-Universe project URLs. Git history shows inherited Apache licensing files were removed. Code and task data therefore remain reconstruction-only pending legal review. The history also previously tracked an environment file; its values were not inspected, but redistributing repository history would require an independent secret scan.

### Proposed importer boundary

`McpAttackSpecImporter` may accept only local, synthetic, declarative pattern specifications. It should normalize manifests, transition triggers, expected call ordering, local effect assertions, reset requirements, provenance, and license status. It must strip or reject code, commands, URLs, credentials, host paths, external transports, and desktop automation. Its first version must compile only to local mock MCP scenarios.

## MCP-Universe

### Locked source

- Repository: https://github.com/SalesforceAIResearch/MCP-Universe
- Commit: `48b453021694d9823d308627fb7f6b7edd29541a`
- Commit date: `2026-06-23T09:01:43+00:00`
- License: Apache-2.0
- Data license: `REVIEW_REQUIRED` for task data and external-service assets
- Dirty checkout: false

### Files inspected

- Project and licensing: `README.md`, `LICENSE.txt`, `license_info.md`, `pyproject.toml`
- Source relationship and submodule: `.gitmodules`, `third_party/mcpmark/LICENSE`, `third_party/mcpmark/README.md`
- Baseline task lifecycle: `mcpuniverse/benchmark/task.py`, `runner.py`, `prepares.py`, `cleanups.py`
- Evaluation and traces: `mcpuniverse/evaluator/evaluator.py`, `mcpuniverse/tracer/types.py`
- MCP management: `mcpuniverse/mcp/manager.py`, `mcpuniverse/mcp/configs/server_list.json`

### Task and fixture schema

The current upstream task model covers ordinary question, output format, server list, evaluators, cleanup declarations, optional preparation functions, and server restriction. It does not contain MCP-SafetyBench's attack-specific modification, addition, mutation, injection, tampering, spoofing, or replay fields.

MCPMark is a real git submodule at `third_party/mcpmark`, pinned by the parent gitlink to `a684e7a3069f824bf5230a7cffe0a4de2add7f0d`. It supports additional task and evaluator integrations but is separate from the MCP-SafetyBench fork relationship.

### Environment lifecycle

MCP-Universe connects configured MCP servers, prepares task environments, executes an agent, evaluates results, and resets service state using trace-informed cleanup functions. Many bundled tasks expect live services and credentials. This lifecycle is evidence for provenance and cleanup semantics only; it is not suitable for the first local MCP runtime.

### Observation and trace model

The tracer provides ordered records for model and tool interactions and supports memory, file, and database collectors. Task reset can inspect the recorded calls in reverse order to derive cleanup arguments. This motivates a complete local trace collector and explicit reset controller in the future C1 spike.

### Oracle and evaluator semantics

Evaluators execute configured function pipelines and comparisons over agent output or service state. Their semantics are task-specific and can depend on external accounts. Cleanup success and evaluator success do not automatically prove safe agent behavior. Native scenarios need local service-state assertions and security effects independent of external services.

### Reusable assets

- Baseline task, evaluator, trace, preparation, and cleanup concepts.
- Server-manager and ordered-tool-event vocabulary.
- MCP-SafetyBench fork provenance.
- MCPMark's separately pinned provenance and Apache-2.0 license evidence.

### Assets requiring semantic reconstruction

- Local trusted and malicious server interfaces.
- Deterministic tool registry mutation and trace collection.
- Local evaluator and cleanup assertions with synthetic data.
- Any baseline normal task needed to exercise one of the three selected attacks.

### Assets that must not enter production runtime

- MCP-Universe packages, agents, workflows, service clients, preparers, or cleanups.
- Live-service tasks, credentials, endpoints, account state, or external database state.
- MCPMark code or data without a separate import decision.
- External evaluator results as native security labels.

### License and provenance risks

MCP-Universe code is Apache-2.0. MCPMark separately carries Apache-2.0. Individual task content, service data, downloaded fixtures, and third-party integrations still require asset-level review. MCP-SafetyBench is a divergent source fork, not a declared dependency on the current upstream package.

### Proposed importer boundary

MCP-Universe is a provenance and design reference feeding `McpAttackSpecImporter`; it is not a direct source of first-stage executable assets. Only independently reconstructed local task, trace, evaluator, and cleanup concepts may cross the boundary.

## MCPSecBench

### Locked source

- Repository: https://github.com/AIS2Lab/MCPSecBench
- Commit: `7612c5a3e811dcf01f64e4f2bb324591a2feaaf4`
- Commit date: `2026-03-05T04:17:17+08:00`
- License: MIT
- Data license: `REVIEW_REQUIRED` for experimental records, prompts, labels, screenshots, and third-party UI media
- Dirty checkout: false

### Files inspected

- Project documentation and license: `README.md`, `LICENSE`, `code/README.md`, `code/pyproject.toml`, `data/README.md`
- Normal and malicious servers: `code/addserver.py`, `code/maliciousadd.py`, `code/download.py`, `code/squatting.py`
- Client and automation: `code/client.py`, `code/main.py`, `code/claude_desktop_config.json`, `code/cursor_config.json`
- Network PoCs: `code/mitm.py`, `code/index.js`, `code/cve-2025-6514.py`, `code/sse.py`
- Experimental data: `data/data.json`, `data/experiments.csv`

### Task and fixture schema

The repository is a playground rather than a normalized task corpus. `data/data.json` is an 11-record array with `attack`, `prompt`, and expected-result-instruction fields. The code tree separately contains normal and malicious servers plus desktop/client configuration. The malicious server combines several techniques in one process, including tool poisoning, tool or server squatting, resource leakage, indirect injection, shell execution, and a stateful rug pull.

Tool poisoning is expressed through malicious tool descriptions and overlapping semantics. Tool and server squatting use near-conflicting names and registration order. Rug pull persists call count in `/tmp/state.json`, returns normal behavior initially, then changes later behavior and description. These are useful seed concepts but must be decomposed into isolated deterministic patterns.

### Environment lifecycle

The automated harness launches CLI clients or controls Cursor through PyAutoGUI. It uses Alt-Tab, screenshots, image matching, mouse clicks, clipboard extraction, and repeated desktop conversations. Claude Desktop requires manual screenshot adaptation and configuration. The instructions also require hand-edited absolute paths and local desktop setup.

No conventional automated test suite or CI-backed reset lifecycle was found. Experiments are repeated manually and classified from client output or screenshots. The local state file must be deleted before runs, which is not a sufficient reset contract.

### Observation and trace model

CLI modes inspect textual client output. Cursor mode relies on screenshot templates, approval-button detection, and clipboard content. Experiment CSV values encode success, undetected failure, detected refusal, protected success, or not-applicable. This evidence is product- and UI-specific and cannot be normalized into a reliable native trace without reconstruction.

### Oracle and evaluator semantics

The project reports attack success rate, refusal rate, and protection success rate, with substantial manual verification. Screenshot and keyword outcomes do not prove a structured tool call, service transition, or harmful effect. The malicious server also mixes multiple attack mechanisms, preventing clean attribution.

Native cases must observe server and tool identity, pre/post definitions, ordered calls, synthetic response or effect markers, forbidden calls, and reset state. GUI outcomes and manual labels are reference annotations only.

### Reusable assets

- Attack taxonomy covering tool poisoning, tool/server squatting, rug pull, indirect injection, MITM, DNS rebinding, configuration drift, schema inconsistency, and related threats.
- The conceptual split between a normal server and a malicious server.
- Stateful normal-to-malicious transition ideas.
- Malicious-server seed reference for local reconstruction.

### Assets requiring semantic reconstruction

- A standalone trusted server and malicious server with minimal, synthetic tools.
- Tool-poisoning metadata without embedded commands or secret targets.
- A deterministic rug-pull threshold, versioned definition, changed response marker, and reset.
- Server-addition and selection assertions independent of registration quirks in desktop products.

### Assets that must not enter production runtime

- PyAutoGUI, screenshots, image matching, clipboard scraping, desktop application control, or manual approval clicking.
- Claude Desktop and Cursor configuration files or hard-coded local paths.
- Network PoCs: raw-socket MITM, DNS rebinding, vulnerable OAuth/client demos, or live weather/network servers.
- Raw prompts, expected-result instructions, experiment labels, screenshots, or combined malicious server implementation.
- GUI automation as the formal evaluation runner.

### License and provenance risks

Repository code is MIT. Experimental data has no independent data license statement. Screenshots contain third-party product interfaces and may include environment-specific information. The duplicated `code/data.json` and `data/data.json` records disagree in expected-result instructions, creating a provenance and single-source-of-truth risk. Documentation also contains filename and Python-version drift.

### Proposed importer boundary

Use MCPSecBench as `reference_only`, `attack_taxonomy`, and `malicious_server_seed_reference`. `McpAttackSpecImporter` may consume manually authored, provenance-tagged summaries of its concepts but no upstream code, prompts, configuration, media, network PoCs, or experiment labels. GUI automation is explicitly excluded from the native evaluator.
