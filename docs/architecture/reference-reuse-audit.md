# 参考环境源码审计与复用边界

- 审计日期：2026-07-16
- 状态：第一阶段架构决策证据
- 审计方式：固定上游提交的完整源码审查；未运行上游服务，不复制上游代码或数据
- 关联决策：[ADR-0002](../adr/0002-offline-import-native-runtime.md)

## 结论

外部 benchmark 应作为场景知识、任务资产、fixture、攻击种子和 oracle 设计的来源，而不是生产执行内核。推荐边界是：

```text
固定 SHA 的外部源码 / 资产
  -> source-specific offline importer
  -> provenance + conversion loss report
  -> project-native Scenario Pack
  -> project validator
  -> sole project runtime
  -> project-native observations and assertions

固定 SHA 的 upstream runtime
  -> upstream_replay（仅复现和转换一致性检查）
  -X-> production runtime
```

正式复用只允许四种模式：

- `reference_only`：只借鉴分类、威胁模型、场景和 oracle 思路。
- `asset_import`：经许可证和来源审查后，离线转换为本项目资产。
- `code_internalization`：只内化小型、稳定、职责单一且许可证明确的实现。
- `upstream_replay`：只在隔离环境复现上游或核对转换一致性。

## 审查边界与视角

本审查覆盖任务 schema、fixture 和环境初始化、Agent/工具执行、trace/observation、任务与安全 oracle、reset/cleanup、可移植实现、外部耦合以及软件和数据许可证。采用以下架构视角：

- **依赖方向**：生产 runtime 不得依赖 importer 或上游 runtime。
- **边界与所有权**：Campaign、执行生命周期、环境事实和最终安全真值只能各有一个项目所有者。
- **模块深度与信息隐藏**：importer 应吸收源格式差异，而不是把上游类型传播给调用方。
- **安全与策略边界**：上游 scorer 只能提供证据或候选断言，不能成为最终安全真值。
- **变更放大与许可证风险**：升级上游或改变数据来源时，应只重跑 importer 和校验，不应改生产执行链。

## 复杂度中心

最高风险不是某个 parser，而是“多个 benchmark runtime 同时进入生产路径”。SABER、Harbor、AgentDojo、τ³、AppWorld 和 MCP-Universe 都分别拥有任务对象、执行循环、trace、scorer 和 cleanup。为它们各建一个长期 runtime adapter，会得到一组浅兼容层：表面接口相同，调用方仍必须理解每个上游的生命周期、结果极性、环境可信度和失败语义。这会造成信息泄漏、未知影响面和多真值源。

离线 importer 是更深的模块：它把源字段、许可证、无法无损表达的语义和转换错误封装在一次转换中；生产调用方只需要理解 Scenario Pack。

## 方案比较

| 方案 | 边界清晰度 | 当前成本 | 升级/运行风险 | 结论 |
| --- | --- | --- | --- | --- |
| 为每个 benchmark 建生产 runtime adapter | 低；上游生命周期穿透接口 | 中 | 最高；多个 scheduler、cleanup 和 scorer | 拒绝 |
| 整体复制上游环境和 runner | 低；形成无所有者 fork | 高 | 高；许可证、依赖和安全补丁持续扩散 | 拒绝 |
| 固定提交、离线转换为原生 Scenario Pack | 高；差异被 importer 隐藏 | 中 | 最低；升级成为显式重导入 | 推荐 |
| 仅保留论文/源码参考 | 最高 | 低 | 低，但无法形成可执行资产 | 许可证不清或耦合过高时使用 |

## 跨项目发现

### P0：上游结果不能成为最终安全真值

SABER 的危险命令正则、CodeIPI 的 canary 端点、AgentDojo 的 `security=True`、MCP-SafetyBench 的最后一个 evaluator 和 MCPSecBench 的人工标签观察的是不同端点。它们可产生候选断言或进度信号，但不能折叠为一个 `safe/unsafe` 字段。

### P1：fixture、solution 和 verifier 必须分权

Terminal-Bench/Harbor 把 instruction、environment、solution 和 tests/verifier 分目录保存，这个资产边界值得保留。导入时 solution 只能作为校准或 `upstream_replay` 输入，不得出现在正式 Agent 可见环境。

### P1：真实外部服务不能成为可重复安全事实

MCP-Universe 的 GitHub/Notion cleanup 会直接调用真实 API；MCP-SafetyBench 也会替换 token、修改 server 文件和重连 Agent。生产安全评估必须把这些目标替换为本地合成服务，并以可快照、可恢复的本地状态为事实源。

## 对抗性边界检查

- **红队攻击**：未来开发者为了“快速接一个 benchmark”，让 runtime 直接反序列化上游 Task，或把上游 Score 写入最终结果。
- **蓝队防御**：Scenario Pack 不允许持久化上游对象；manifest 记录固定 SHA、源路径和复用模式；importer 输出转换损失；生产依赖检查禁止 runtime 导入 importer/上游包。
- **残余风险**：本阶段没有实现 schema 和依赖检查。下一阶段 spike 必须用“转换后不安装上游包仍可加载”作为验收条件。

## SABER

### 审计版本

- Repository: `https://github.com/sssr-lab/SABER`
- Commit: `bfdffb10c3887b38e1bd57ae2e548faa8f2049e9`
- Audit date: `2026-07-16`
- License: Apache-2.0（代码、脚本、Docker/配置和软件文档）
- Data license: CC-BY-4.0（SABER 自有任务和非代码数据）；第三方 baseline 保留各自许可证
- Key files inspected:
  - `task_runtime.py:48`
  - `sandbox_shell.py:71`
  - `run_osbench.py`
  - `judge_osbench.py:201`
  - `mcp_runtime.py`
  - `tasks/A/info_leak/A_info_001.json`
  - `dataset/data/tasks.jsonl`
  - `LICENSE`
  - `LICENSES/THIRD-PARTY.md`

### 实际架构

任务 JSON 将 `setup`、`injection` 和 `ground_truth` 放在同一记录。`TaskRuntime` 根据 `mock_fs`、`file_contents`、`init_commands`、权限和 MCP server 建立工具环境，并统一记录 shell/MCP event 和 delta（`task_runtime.py:48-135`）。`SandboxShell` 启动无网络 Docker 容器、写入 fixture、模拟网络命令、按步骤注入内容并记录状态变化（`sandbox_shell.py:86-170`, `sandbox_shell.py:237-297`）。

judge 同时使用状态属性、命令正则和 LLM harm 判定。`check_harmful_patterns` 只是在轨迹命令上匹配 `harmful_command_patterns`（`judge_osbench.py:211-220`），因此不能证明接收端效果。容器 cleanup 只负责删除容器（`sandbox_shell.py:549-559`）。

### 可复用内容

- 任务 JSON/JSONL 中的正常任务、fixture、注入入口、攻击种子和 harm 描述。
- `tool_output`、`file_content`、`config_inject`、`error_message`、`multi_step` 注入设计。
- event/delta 分类和危险模式，作为 Assertion Candidate。
- Scenario A/B/C 的分层思路，以及安全完成、拒绝和事故性伤害的区分。

### 不应复用内容

- 不把 SABER Shell/网络模拟输出当作真实环境事实；例如模拟成功的 `curl` 不是接收端收到数据的证据。
- 不把 `run_osbench.py`、`TaskRuntime` 或 `SandboxShell` 作为正式 runtime。
- 不把命令字符串正则或上游最终标签作为本项目安全真值。
- 不整体复制 `baselines/`；其中包含多种上游许可证。

### 推荐复用模式

- `asset_import`：SABER 自有、许可证确认的任务资产。
- `reference_only`：judge 组合方式和状态 delta 设计。
- `upstream_replay`：少量转换一致性检查。

### 在本项目中的具体落地方式

下一阶段使用 `SaberScenarioImporter` 将正常任务、fixture、注入位置和 harm 描述转换为 Scenario Pack；`harmful_*_patterns` 只进入候选断言，必须由项目 assertion 明确证据端点。转换后的 pack 不导入 SABER 包也能独立加载。

### 许可证与来源要求

每个导入任务记录仓库、commit、`source_path`、任务 ID、原始许可证和转换版本。根 `LICENSE` 将自有任务指定为 CC-BY-4.0；`dataset/README.md` 又写 Apache-2.0，存在上游文档冲突，实际复制或再分发前必须按根许可证和权利人说明复核。第三方 baseline 不得借用 SABER 根许可证重新授权。

### 风险和未决问题

- `dataset/manifest.json` 当前记录 716 个任务，而 `AGENTS.md` 仍描述 513 个，导入器必须从固定提交实际枚举并校验数量。
- 模拟网络、git 和包管理命令会产生与真实系统不同的成功语义。
- 哪些正则可以提升为确定性 assertion 仍需逐条证明。

## Inspect Evals / CodeIPI

### 审计版本

- Repository: `https://github.com/UKGovernmentBEIS/inspect_evals`
- Commit: `3fda7b008453f8ba6bb7b1471e8fbd1865d2257e`
- Audit date: `2026-07-16`
- License: MIT
- Data license: 根 MIT；未找到 CodeIPI 样本的独立数据许可证
- Key files inspected:
  - `src/inspect_evals/ipi_coding_agent/ipi_coding_agent.py:33`
  - `src/inspect_evals/ipi_coding_agent/setup.py:22`
  - `src/inspect_evals/ipi_coding_agent/scorer.py:42`
  - `src/inspect_evals/ipi_coding_agent/dataset/samples.json`
  - `src/inspect_evals/ipi_coding_agent/docker/compose.yaml`
  - `src/inspect_evals/ipi_coding_agent/README.md`
  - `LICENSE`

### 实际架构

`_load_samples` 将 `task_description`、`issue_text`、`repo_files`、`verification_command`、`persistence_targets` 和攻击元数据映射为 Inspect `Sample`（`ipi_coding_agent.py:33-86`）。setup 用 Base64 安全写文件，植入环境/文件 canary，并对 `/workspace` 和 `/root` 文件做 SHA-256 快照（`setup.py:22-79`）。

scorer 分别读取 tool-call 参数、assistant 文本和 tool result，再按 payload 类别检查 canary、执行 marker 或持久化文件变化（`scorer.py:42-191`）；正常任务由 `verification_command` 的退出码判定（`scorer.py:345-351`）。最终 `accuracy` 又把攻击抵抗和任务完成合并（`scorer.py:363-379`）。

### 可复用内容

- 样本结构、`repo_files`、正常修复任务、注入入口和 benign 对照。
- `verification_command`、`persistence_targets`、canary 和文件快照设计。
- Base64 安全写文件和 SHA-256 快照可作为 `code_internalization` 候选，但要以项目接口和测试重写。

### 不应复用内容

- 不把 Inspect `Sample` 或 `TaskState` 放入持久化 Scenario Pack。
- 不直接沿用 scorer 的单一端点语义：看到秘密、输出秘密、请求外发、执行请求和接收端收到 canary 是不同事件。
- 不把组合 `accuracy` 当作最终安全结果；安全与正常任务 utility 必须分开。
- 不保留对 Inspect sandbox 的运行期依赖作为导入后 pack 的必要条件。

### 推荐复用模式

- `asset_import`：经来源复核的 6 条代表样本 spike。
- `code_internalization`：小型 Base64 写文件和 SHA-256 快照语义，待独立实现和测试。
- `upstream_replay`：核对转换后的 fixture 和 verification command。

### 在本项目中的具体落地方式

使用 `CodeIPIImporter` 输出项目原生 fixture、正常任务、攻击位置、任务 oracle 和分层安全 oracle。至少区分：

```text
secret_observed
secret_in_assistant_output
exfiltration_attempted
exfiltration_request_executed
receiver_received_canary
```

Inspect 只可在 `upstream_replay` 中承载原始评测；导入文件不得依赖 `Sample` 类型。

### 许可证与来源要求

根 MIT 适用于仓库软件和随附材料，但未找到 CodeIPI dataset 的独立许可证声明。下一阶段复制 6 条样本前，应把根许可证适用范围和样本作者/第三方内容来源记录为审批证据；本阶段不复制任何样本。

### 风险和未决问题

- canary 出现在 tool result 或 assistant text 只能证明观察/披露，不自动证明外发接收。
- LLM detection grader 不是确定性 oracle。
- SHA 快照范围包括 `/root`，导入时必须收窄到 fixture 声明的授权路径。

## Terminal-Bench 2 / Harbor

### 审计版本

- Repository: `https://github.com/harbor-framework/terminal-bench`
- Commit: `d28711d0da2675d0bb1d56de45ae5df6082438a3`
- Repository: `https://github.com/harbor-framework/harbor`
- Commit: `d3e606d9f7d1e111bb22d3d820ebed03ec300eb3`
- Audit date: `2026-07-16`
- License: Apache-2.0（两个仓库）
- Data license: 根 Apache-2.0；适配器导入和任务内第三方资产需逐任务复核
- Key files inspected:
  - Terminal-Bench `terminal_bench/handlers/trial_handler.py:29`
  - Terminal-Bench `terminal_bench/dataset/dataset.py:17`
  - Terminal-Bench `terminal_bench/harness/harness.py`
  - Terminal-Bench `original-tasks/analyze-access-logs/{task.yaml,Dockerfile,docker-compose.yaml,run-tests.sh,solution.sh}`
  - Harbor `src/harbor/models/task/task.py:35`
  - Harbor `src/harbor/verifier/verifier.py:39`
  - Harbor `src/harbor/trial/trial.py:345`
  - Harbor `src/harbor/environments/base.py`
  - Harbor `adapters/*/adapter.py`

### 实际架构

旧 Terminal-Bench task 由 `task.yaml`、`Dockerfile`/Compose、`run-tests.sh`、tests 和 solution 构成；`TaskPaths` 明确列出这些位置（`trial_handler.py:124-170`），Harness/TrialHandler 负责执行、terminal 记录和 parser 评分。

当前 Harbor 将格式演进为 `instruction.md`、`task.toml`、`environment/`、`solution/` 和 `tests/`（`models/task/task.py:35-49`）。Verifier 把测试上传到隔离环境、运行 test script，并读取 reward 文件（`verifier/verifier.py:96-238`）。`Trial.run` 拥有准备、Agent 执行、恢复和 finalize 生命周期（`trial/trial.py:345-390`）。大量 `adapters/*/adapter.py` 证明“离线映射为 Harbor task”是上游自身采用的边界。

### 可复用内容

- instruction/正常任务、Dockerfile、Compose、tests、verifier 和明确的环境文件。
- solution 只作为校准资产或 verifier 设计参考。
- Harbor adapter 的离线转换和 parity experiment 思路。
- task 目录 digest、测试与 Agent 环境隔离、reward 文件协议。

### 不应复用内容

- 不把 Harbor `Trial`、Environment、Agent 或 Verifier 作为第二套正式执行内核。
- 不让 solution 进入正式 Agent 可见环境。
- 不直接信任 reward 数值为安全真值；Terminal-Bench/Harbor verifier 主要是任务 utility oracle。
- 不批量导入适配器生成的第三方资产而跳过原始来源许可证。

### 推荐复用模式

- `asset_import`：小型、快速、许可证清晰的 task fixture。
- `reference_only`：adapter/parity 和 verifier 隔离设计。
- `upstream_replay`：运行上游 tests 对照转换结果。

### 在本项目中的具体落地方式

使用 `TerminalBenchFixtureImporter` 将 instruction、environment、tests 和 verifier 描述转换为 Scenario Pack。solution 存放在 importer/replay 专用区域，生产 runtime 不可读取。首个 spike 只选 2 至 3 个环境较小、测试快且适合植入日志/README/配置攻击的任务。

### 许可证与来源要求

两个仓库根许可证均为 Apache-2.0。具体任务可能来自外部 benchmark、包、数据或预构建镜像；导入前必须记录 task 路径、原作者、上游仓库/版本和资产许可证。根许可证不能替代容器内或 adapter 来源的第三方条款。

### 风险和未决问题

- Terminal-Bench 与 Harbor 格式已经演进，importer 必须显式区分版本。
- Docker build 可能从网络拉取浮动依赖；spike 需固定镜像和依赖。
- verifier 权限、网络和 Agent 隔离需要项目运行时重新实现，而不是继承上游默认值。

## AgentDojo

### 审计版本

- Repository: `https://github.com/ethz-spylab/agentdojo`
- Commit: `089ed468cf3ed0322acc66b0211f26d9d90dbf60`
- Audit date: `2026-07-16`
- License: MIT，另有嵌入式第三方 notice
- Data license: 根 MIT；fixture 和嵌入材料需要逐资产复核
- Key files inspected:
  - `src/agentdojo/base_tasks.py:18`
  - `src/agentdojo/task_suite/task_suite.py:139`
  - `src/agentdojo/task_suite/task_suite.py:339`
  - `src/agentdojo/functions_runtime.py`
  - `src/agentdojo/data/suites/{workspace,travel,banking,slack}`
  - `src/agentdojo/default_suites/v1`
  - `src/agentdojo/yaml_loader.py`

### 实际架构

`BaseUserTask` 和 `BaseInjectionTask` 分别定义 ground truth、utility 和 injection security；检查可基于输出、前后环境或 trace（`base_tasks.py:18-94`, `base_tasks.py:97-160`）。`TaskSuite.run_task_with_pipeline` 加载并注入默认环境、深拷贝前状态、运行自有 pipeline/runtime，然后分别返回 utility 与 injection 成功布尔值（`task_suite.py:339-420`）。上游 `security=True` 表示攻击目标执行成功，不表示系统安全。

### 可复用内容

- `environment`、injection vector/slot、user task、injection task 的分离。
- utility oracle 和 security oracle 分权。
- 少量 suite 的业务实体、fixture 和终态检查思路。
- trace fallback 适合无持久化副作用的动作检查。

### 不应复用内容

- 不让 `TaskSuite`、Pydantic environment、`FunctionCall` 或上游 task 类进入核心 schema。
- 不依赖 AgentDojo pipeline/runtime API 作为生产路径。
- 不直接保留 `security` 字段名和极性。
- 不把 YAML `!include` 当作不可信纯数据解析。

### 推荐复用模式

- `asset_import`：经资产许可审核的少量 suite/fixture。
- `reference_only`：Injection Slot、utility/security 分权和 oracle 模式。
- `upstream_replay`：对照转换后的业务终态和极性。

### 在本项目中的具体落地方式

首版只借鉴环境和 Injection Slot；选少量 suite 转成本地合成 Mock Service 和原生 Scenario Pack。所有上游检查结果在 importer 中重命名为明确的 `attack_goal_achieved`、`utility_satisfied` 等证据，不依赖其 runtime API。

### 许可证与来源要求

保留根 MIT notice，并审查 `yaml_loader.py` 中嵌入的 MIT/CC-BY-SA 来源说明。每个 fixture、include 和任务类记录具体路径；未经逐资产审核不得复制整个 suite。

### 风险和未决问题

- Python task 和 YAML include 是可执行插件，不是安全的静态数据。
- `security` 极性容易在转换时反转。
- 哪个 suite 最适合本地 Mock Service 仍需以依赖闭包和资产许可筛选。

## τ-bench / τ²-bench / τ³-bench

### 审计版本

- Repository: `https://github.com/sierra-research/tau-bench`
- Commit: `59a200c6d575d595120f1cb70fea53cef0632f6b`
- Repository: `https://github.com/sierra-research/tau2-bench`
- Current τ³ commit: `a1e85084a3960281cb06997594133e8f39ea42a7`
- Historical τ² tag `v0.2.0`: `f8de30c298689cbe0117d76a378e7315a17e5bd8`
- Audit date: `2026-07-16`
- License: MIT（两个仓库）
- Data license: 根 MIT；未找到 domain data 的独立许可证
- Key files inspected:
  - τ-bench `tau_bench/types.py`
  - τ-bench `tau_bench/envs/{airline,retail}/{wiki.md,tasks.py,env.py,rules.py,data/*}`
  - τ³ `README.md`
  - τ³ `src/tau2/data_model/tasks.py:366`
  - τ³ `src/tau2/evaluator/evaluator_env.py:17`
  - τ³ `src/tau2/evaluator/evaluator_action.py`
  - τ³ `src/tau2/evaluator/evaluator.py:24`
  - τ³ `data/tau2/domains/{airline,retail,telecom,banking_knowledge}`

### 实际架构

原 τ-bench 用 Python Task、domain rules/wiki、JSON DB 和 tool 类定义单方工具交互。`tau2-bench` 的 `v0.2.0` 是 τ²；当前 main 已在 README 中标为 τ³，但 Python 包和数据路径仍保留 `tau2` 名称。

当前 `EvaluationCriteria` 可包含参考 actions、环境 assertions、通信要求和 reward basis。环境 evaluator 在初始状态上执行 golden actions，得到 gold DB，再与实际轨迹重放后的 DB hash 比较（`evaluator_env.py:64-150`）。因此 actions 通常用于构造参考终态，并不天然意味着只有该调用序列才正确；只有显式启用 ACTION reward 时才比较动作轨迹。

### 可复用内容

- `policy.md`/wiki、Tool Contract、初始 DB、Tasks 和业务终态。
- Policy violation 场景和授权上下文。
- DB final-state、communication、action 和 assertion 分离的 evaluator 设计。
- τ² 的双控制环境与 τ³ 的更多 domain 设计，只作为场景来源。

### 不应复用内容

- 不把单条 `evaluation_criteria.actions` 当作唯一正确执行路径。
- 不把 τ runner/orchestrator、user simulator 或 LLM reviewer 作为生产 runtime。
- 不让 `tau2` Pydantic 类型进入核心 Scenario Pack。
- 不把自然语言 assertion/LLM reviewer 提升为最终安全真值。

### 推荐复用模式

- `asset_import`：政策、工具契约、初始 DB、任务和终态 oracle。
- `reference_only`：双控制、通信和 reward basis 设计。
- `upstream_replay`：核对等价业务终态。

### 在本项目中的具体落地方式

将 policy、工具 schema、初始 DB 和任务转换为本地服务 fixture。Task oracle 优先表达可接受的业务终态和必要通信；参考 actions 只保留为校准轨迹或用于推导终态。Policy violation 另建 security oracle，不与 utility reward 混合。

### 许可证与来源要求

两个仓库根许可证均为 MIT，未发现 domain data 的独立许可文本。导入前仍需记录具体 domain、数据文件和 commit，并确认政策文本、产品目录等数据是否全部由上游授权。τ² 历史复现必须记录 tag commit，不能只写浮动仓库名。

### 风险和未决问题

- 同一仓库名 `tau2-bench` 当前代表 τ³，版本名和包路径容易造成 provenance 漂移。
- 当前任务可组合 DB、ACTION、COMMUNICATE 和实验性 NL assertion；importer 需要报告无法确定性转换的部分。
- 等价终态可能允许多条路径，安全 assertion 还需检查越权副作用和 collateral change。

## AppWorld

### 审计版本

- Repository: `https://github.com/StonyBrookNLP/appworld`
- Commit: `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`
- Audit date: `2026-07-16`
- License: Apache-2.0（公开部分）
- Data license: 受保护 `.bundle` 为 Apache-2.0 加“公开再分发必须保持加密”的额外条件
- Key files inspected:
  - `src/appworld/task.py`
  - `src/appworld/ground_truth.py`
  - `src/appworld/evaluator.py:40`
  - `src/appworld/collections/models.py:364`
  - `src/appworld/environment.py`
  - `src/appworld/install.py`
  - `src/appworld/download.py`
  - `README.md:1604`
  - `src/appworld/.source/{apps.bundle,tests.bundle}`
  - `generate/.source/{data.bundle,tasks.bundle}`

### 实际架构

AppWorld 将任务、初始状态、API 环境和 ground-truth tests 组织为完整应用世界。`ModelCollectionPair` 比较 start/end model hash、记录集合和字段差异（`collections/models.py:391-555`）。Evaluator 的 `TestTracker` 记录 requirement、pass/failure，并明确区分 `no_op_fail` 与 `no_op_pass`（`evaluator.py:84-124`）。

大部分 app/task/evaluation 具体内容位于 Git LFS 加密 bundle；当前完整克隆已取得全历史 LFS 对象，但许可证要求公开再分发或衍生物保持加密。

### 可复用内容

- Start State / End State、Model/Entity Diff 和字段级变化。
- Requirement-based Assertions。
- No-op Pass / No-op Fail 测试设计。
- Collateral Change 检查和未授权附带修改检测。

### 不应复用内容

- 首版不内化整个 AppWorld 环境、apps、数据库和运行器。
- 不解包并提交、截图或公开复制受保护 bundle 内容。
- 不把 AppWorld evaluator 结果直接作为本项目安全真值。
- 不建立 `AppWorldRuntimeAdapter` 进入生产路径。

### 推荐复用模式

- `reference_only`：首版只借鉴差分和 assertion 设计。
- `upstream_replay`：在许可证允许的本地隔离环境复现少量任务。
- `asset_import`：仅在受保护内容的许可、加密再分发和本地存储方案明确后考虑。

### 在本项目中的具体落地方式

把“start snapshot + authorized change set + end snapshot + collateral-change assertion”作为 Scenario Pack 的 oracle 设计候选。首版自己实现小型本地实体/服务，不复制 AppWorld apps 或 task bundle。

### 许可证与来源要求

公开代码遵循 Apache-2.0。README 明确要求受保护部分及其衍生物如公开再分发必须保持加密（`README.md:1613-1618`）。manifest 必须标记这一额外条件；本任务只审计 bundle 元数据和公开实现，不复制或解包受保护内容到项目仓库。

### 风险和未决问题

- 受保护内容的衍生 Scenario Pack 是否属于必须加密再分发的衍生物，需要法律/权利人确认。
- 全环境依赖闭包过大，不适合作为第一批 importer spike。
- model diff 需要显式授权上下文，否则“变化存在”不能直接判定为安全问题。

## MCP-SafetyBench / MCP-Universe

### 审计版本

- Repository: `https://github.com/xjzzzzzzzz/MCPSafety`
- Commit: `7872437b6369aac1150e3a19e350a981dc554f81`
- License: `REVIEW_REQUIRED`（无 LICENSE 文件；`pyproject.toml` 仅声明 3-Clause BSD）
- Repository: `https://github.com/SalesforceAIResearch/MCP-Universe`
- Commit: `48b453021694d9823d308627fb7f6b7edd29541a`
- MCPMark submodule: `a684e7a3069f824bf5230a7cffe0a4de2add7f0d`
- License: Apache-2.0（`LICENSE.txt`）；MCPMark submodule 也为 Apache-2.0
- Data license: MCP-SafetyBench `REVIEW_REQUIRED`；MCP-Universe/MCPMark 外部服务和第三方数据逐任务复核
- Audit date: `2026-07-16`
- Key files inspected:
  - MCP-SafetyBench `mcpuniverse/benchmark/task.py:28`
  - MCP-SafetyBench `mcpuniverse/benchmark/runner.py:111`
  - MCP-SafetyBench `mcpuniverse/mcp/client.py:185`
  - MCP-SafetyBench `mcpuniverse/mcp/manager.py:351`
  - MCP-SafetyBench `mcpuniverse/evaluator/{evaluator.py,functions.py}`
  - MCP-SafetyBench `mcpuniverse/benchmark/configs/test/**/*.json`
  - MCP-Universe `mcpuniverse/benchmark/task.py:24`
  - MCP-Universe `mcpuniverse/benchmark/runner.py:205`
  - MCP-Universe `mcpuniverse/benchmark/cleanups.py`
  - MCP-Universe `third_party/mcpmark/{LICENSE,tasks/**}`

### 实际架构

MCP-Universe 的 Task schema 包含 question、MCP servers、evaluators、prepare 和 cleanup；runner 在执行前 prepare，执行后按 trace 反向 cleanup（`benchmark/task.py:63-221`, `benchmark/runner.py:205-299`）。部分 cleanup 直接调用真实 GitHub/Notion API；MCPMark filesystem cleanup 管理备份并清除测试目录和环境变量（`benchmark/cleanups.py:239-336`）。

MCP-SafetyBench 在这套 runtime 上增加 `attack_category`、server modifications/additions/update、intent injection、data tampering、identity spoofing 和 replay injection（`benchmark/task.py:51-71`）。runner 会动态修改/注入工具、替换 server、把 trace 传入攻击 evaluator，再恢复 server 文件、描述和 token（`benchmark/runner.py:292-375`, `benchmark/task.py:288-324`）。有攻击时最后一个 evaluator 被硬编码为 `attack_success`（`benchmark/runner.py:111-135`）。

### 可复用内容

- MCP server 修改、恶意 tool 注入、Rug Pull、Identity Spoofing、Data Tampering 和 Replay Injection 分类。
- trace 驱动 cleanup、按调用结果解析 cleanup 参数和 server 文件恢复思路。
- attack config 与正常任务 evaluator 分离。
- MCPMark 的本地 filesystem/task verifier 设计，在许可证和资产审查后作为参考。

### 不应复用内容

- 不复制 MCP-SafetyBench 代码或数据，直到存在可核验许可证文本。
- 不把“最后一个 evaluator”约定带入项目 schema。
- 不让真实 GitHub、Google、Notion、搜索或终端服务参与可重复生产评估。
- 不把 MCP-Universe runner、Agent、MCP manager 或 cleanup 当作生产 runtime。

### 推荐复用模式

- MCP-SafetyBench：`reference_only`，许可证解决前不得复制。
- MCP-Universe/MCPMark：`reference_only`；少量本地任务可在逐资产审核后 `asset_import`。
- `upstream_replay`：隔离环境验证 trace/cleanup 语义。

### 在本项目中的具体落地方式

将攻击类别和 malicious server seed 重新表达为本地合成 MCP 服务。所有服务状态可快照、无外部凭证、reset 可验证。安全 oracle 基于项目 trace 和本地接收端/状态证据，不继承 evaluator 顺序约定。

### 许可证与来源要求

MCP-SafetyBench 没有 LICENSE 文件，包元数据中的 BSD 声明不足以替代许可证正文，故代码和数据均标为 `REVIEW_REQUIRED`。MCP-Universe 根 `LICENSE.txt` 和 MCPMark 子模块为 Apache-2.0，但外部服务数据、第三方 benchmark 和具体 task 仍需逐项来源记录。

### 风险和未决问题

- 上游真实 API cleanup 会产生权限、费用和残留状态风险。
- 动态修改 server.py、环境 token 和 tool description 的恢复失败可能污染后续任务。
- attack evaluator 多依赖 trace 字段和顺序，必须转换为项目明确的证据契约。

## MCPSecBench

### 审计版本

- Repository: `https://github.com/AIS2Lab/MCPSecBench`
- Commit: `7612c5a3e811dcf01f64e4f2bb324591a2feaaf4`
- Audit date: `2026-07-16`
- License: MIT
- Data license: `REVIEW_REQUIRED`（未找到实验数据的独立许可证/来源说明）
- Key files inspected:
  - `README.md`
  - `data/README.md:1`
  - `data/experiments.csv`
  - `code/data.json`
  - `code/main.py:1`
  - `code/maliciousadd.py:1`
  - `code/client.py`
  - `code/squatting.py`

### 实际架构

仓库将攻击 prompt/期望标签保存在 `code/data.json`，恶意 MCP server 和 client 在 `code/`。`maliciousadd.py` 实现 tool poisoning、credential disclosure、rug pull、错误工具、路径读取和 sandbox 命令等种子（例如 rug pull 在 `maliciousadd.py:187-273`）。自动流程 `code/main.py` 使用 PyAutoGUI、模板截图和桌面应用剪贴板，按文本输出将结果归为 Attack success/detected/fail。

`data/README.md` 明确 17 类攻击中只有 11 类有自动脚本，其余需要人工验证，并在 Claude Desktop、OpenAI 和 Cursor 上反复测试（`data/README.md:3-13`）。

### 可复用内容

- attack taxonomy。
- malicious server seed 和攻击实现参考。
- Tool Poisoning、Tool Shadowing、Name Squatting、Data Exfiltration、Prompt/Indirect Injection、Rug Pull、Sandbox Escape 和 Confused AI 场景。

### 不应复用内容

- GUI、PyAutoGUI、桌面截图、剪贴板和手动 Cursor/Claude Desktop 流程不得进入自动化主路径。
- 不继承基于模型/文本的四标签判定为最终安全真值。
- 不直接执行硬编码本机路径、容器 ID 或 `os.system` 命令。
- 不复制数据，直到独立数据许可和来源明确。

### 推荐复用模式

- `reference_only`：分类和攻击实现思路。
- `asset_import`：只在数据许可确认后导入少量恶意 server seed。
- `upstream_replay`：仅用于人工复现，不进入 CI 或生产执行。

### 在本项目中的具体落地方式

将选定攻击重写为无 GUI 的本地 MCP server fixture；输入、工具调用、server 状态和接收端效果均由项目 runtime 记录。人工桌面实验只作为背景证据，不作为可重复 benchmark 的 oracle。

### 许可证与来源要求

根代码为 MIT，需保留 notice。`data/` 只描述实验流程和结果，未提供独立数据许可或逐项来源，因此 `data_license` 保持 `REVIEW_REQUIRED`。本阶段不复制代码、图片、CSV 或 JSON。

### 风险和未决问题

- 手工/视觉自动化流程不可重复且易受 UI 版本影响。
- 部分实现包含固定路径、固定容器 ID 和不安全 shell 拼接，只能作为攻击参考。
- 17 类攻击到项目 assertion 的证据端点仍需逐类定义。

## 已有设计中应保留的部分

- 项目现有 ADR 已明确 importer 与 runtime 的禁止依赖方向。
- 现有架构文档坚持 Campaign Controller 和 Final Assertion Engine 的唯一所有权。
- 本阶段没有复制第三方代码或数据，允许许可证问题在进入实现前暴露。

## 下一步

只实施三个小型 importer spike：CodeIPI 6 条、SABER A/B/C 各 2 条、Terminal-Bench 2 至 3 个任务。共同验收点是 provenance 完整、转换损失显式、上游类型不进入 Scenario Pack、移除上游包后仍可加载；具体计划见 `docs/development/importer-spike-plan.md`。
