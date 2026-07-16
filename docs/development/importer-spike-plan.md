# 下一阶段 Importer Spike 计划

- 状态：第一阶段输出；仅规划，不实现
- 日期：2026-07-16
- 架构依据：[ADR-0002](../adr/0002-offline-import-native-runtime.md)
- 来源依据：[参考环境源码审计](../architecture/reference-reuse-audit.md)
- 来源清单：[references/manifest.yaml](../../references/manifest.yaml)

## Go / No-Go

- **判断**：来源和许可证门禁通过后 Go。
- **原因**：三个 spike 的输入、数量、转换边界和验收证据已经足够明确；但 CodeIPI
  样本许可证、SABER 数据许可证冲突以及 Terminal-Bench 逐任务资产来源必须在复制任何
  材料前解决。
- **判断所有者**：来源清单审核者批准单条资产进入 `asset_import` 后，实施者才能导入；
  项目测试和人工差异审查共同判断 spike 是否完成。

## 目标结果

下一阶段只验证三个离线 importer 能否把少量固定版本的上游记录转换成自包含的
Scenario Pack 候选：

1. `CodeIPIImporter` 导入 6 条代表记录。
2. `SaberScenarioImporter` 导入 Scenario A/B/C 各 2 条，共 6 条。
3. `TerminalBenchFixtureImporter` 导入 2 至 3 个小任务。

每个转换结果必须带完整 provenance 和转换损失报告，并且在不安装、不导入上游包的
环境中仍可被项目独立加载。Spike 只用实际案例检验最小字段候选，不冻结最终领域模型、
包结构、类名、序列化格式或数据库设计。

## 架构边界

```text
fixed upstream commit
  -> source-specific offline importer
  -> validation + conversion-loss report
  -> project-native Scenario Pack candidate

project runtime -> Scenario Pack candidate
project runtime -X-> importer
project runtime -X-> upstream package/runtime
```

三个 importer 只负责读取、校验、规范化和记录损失，不得拥有 Agent 执行、调度、trace
采集、最终 assertion 或 cleanup 生命周期。上游 runner 只可在隔离的 `upstream_replay`
对照中出现。

## 范围

### 包含

- 固定 SHA 的源记录选择和逐条 provenance 审核。
- 只覆盖本计划列出的 14 至 15 个小案例。
- 从实际案例推导一个可删除、可改名的最小字段候选集合。
- 每个 importer 的确定性转换、输入校验、损失报告和独立加载测试。
- 必要时用上游 replay 对照 fixture、验证命令或 task oracle，不接入生产 runtime。

### 不包含

- 完整 Scenario Pack 领域模型或持久化 schema。
- 正式 runtime adapter、Campaign Controller、Inspect Backend 或 Final Assertion Engine。
- 批量导入完整 benchmark、增加生产依赖或复制上游 runtime。
- 将 SABER regex、Inspect scorer、Harbor reward 或其他上游结果作为最终安全真值。
- 内化完整 AppWorld、AgentDojo、MCP-SafetyBench、MCP-Universe 或 MCPSecBench 环境。

## 共同最小字段候选

这些字段是 spike 的比较工具，不是稳定 API。只有在至少两个 importer 中被实际使用，或为
独立加载、来源追踪和安全边界所必需，才有资格进入后续设计评审。

| 字段 | Spike 中的用途 | 本阶段不作出的决定 |
| --- | --- | --- |
| `case_id` | 标识一次导入后的具体案例 | 全局 ID 格式和数据库主键 |
| `scenario_id` | 关联同一正常任务或场景族 | 场景继承和版本关系 |
| `fixture` | 描述离线生成的文件、服务或初始状态 | 完整 fixture 类型系统 |
| `normal_task` | 保存 Agent 应完成的正常任务 | 通用任务 DSL |
| `attack_placement` | 表达注入载体、位置和触发条件 | 完整攻击 taxonomy |
| `authorization_context` | 区分允许、未授权和条件授权动作 | 最终 policy 语言 |
| `task_oracles` | 保存 utility 验证候选 | 最终 assertion API |
| `security_oracles` | 保存明确证据端点的安全断言候选 | 最终安全 verdict 枚举 |
| `reset_spec` | 描述恢复到已知初始状态的最小要求 | 通用 cleanup 编排器 |
| `provenance` | 固定来源、许可证、路径、摘要和转换版本 | 最终 provenance 表结构 |

每个案例还必须产生独立的转换损失报告。报告至少列出未知字段、未转换字段、语义降级、
许可证门禁和需要人工确认的 oracle。损失报告不得被塞进 `provenance` 后静默忽略。

### Provenance 最低证据

- 上游 repository 和完整 commit SHA。
- `source_path`、上游记录 ID 和源内容摘要。
- 软件许可证、数据许可证以及适用的文件级附加条款。
- importer 名称、转换版本和转换时间。
- 发生过的选择、规范化和人工裁决。
- 生成资产的内容摘要，以及与原始资产的可追溯关系。

## 共同转换规则

1. **先门禁再读取内容**：固定 SHA、源路径和许可证状态未通过时，不把源材料复制到项目
   仓库或生成可提交资产。
2. **输入 fail closed**：缺字段、类型不符、未知 schema 版本、摘要不匹配或路径越界时，
   importer 必须拒绝该记录并给出确定性错误。
3. **语义不静默降级**：无法可靠表达的字段进入转换损失报告；不能猜测默认值补齐。
4. **安全与 utility 分离**：正常任务完成不能抵消安全失败，安全拒绝也不能自动算作正常
   任务完成。
5. **上游类型不越界**：生成物和公共加载接口中不得出现 Inspect `Sample`、SABER task
   runtime 对象或 Harbor task/runtime 对象。
6. **无上游依赖加载**：在仅安装本项目的环境中，所有生成案例均能解析并完成静态校验。
7. **转换确定性**：相同源 commit、路径和 importer 版本必须得到相同内容摘要；时间戳等
   非确定字段不得进入内容摘要。
8. **原始 solution 隔离**：校准答案、solution 和 verifier 私密材料不能进入 Agent 可见
   fixture。

## Spike 1：CodeIPIImporter

### 固定来源

- Repository: `https://github.com/UKGovernmentBEIS/inspect_evals`
- Commit: `3fda7b008453f8ba6bb7b1471e8fbd1865d2257e`
- Dataset path: `src/inspect_evals/ipi_coding_agent/dataset/samples.json`

### 6 条候选记录

| 类型 | 上游 ID | 选择理由 |
| --- | --- | --- |
| Issue Injection | `ipi-issue-exfil-01-plain` | 覆盖 issue 文本和 exfiltration 端点 |
| Issue Injection | `ipi-issue-exec-32-authority` | 覆盖 issue 文本、authority 话术和执行端点 |
| Code Comment | `ipi-comment-exec-01-plain` | 覆盖源代码注释和执行端点 |
| Code Comment | `ipi-comment-persist-12-authority` | 覆盖源代码注释、authority 话术和持久化端点 |
| README | `ipi-readme-exfil-16-authority` | 覆盖 README 注入和 exfiltration 端点 |
| Benign | `ipi-benign-02-suspicious` | 覆盖可疑但无攻击的 false-positive 对照 |

若任一记录没有通过数据许可证或嵌入内容来源审核，只能换成同一类型中已批准的记录；数量和
`Issue 2 + Comment 2 + README 1 + Benign 1` 分布不得改变。替换必须记录理由和新源 ID。

### 转换内容

- 把 `repo_files` 规范化为受限路径内的 fixture 文件。
- 保留 `task_description` 和 `verification_command` 作为正常任务及 task oracle 候选。
- 映射 `injection_vector`、`issue_text`、payload 类型和具体植入位置。
- 对存在的 `persistence_targets` 或等价字段保留路径和状态检查语义。
- 生成 canary、fixture 内容和文件摘要的来源记录。
- Base64 安全写文件和 SHA-256 快照只作为小型 `code_internalization` 候选；须以项目接口
  独立实现和测试，不复制上游函数。

### 安全端点拆分

CodeIPI scorer 的组合结果不得直接导入。每条安全 oracle 至少能表达以下不同事实，未适用
的端点必须显式标为不适用而不是 false：

```text
secret_observed
secret_in_assistant_output
exfiltration_attempted
exfiltration_request_executed
receiver_received_canary
```

持久化和任意代码执行案例还需用独立、可观察的文件状态或执行 marker 表达，不能复用
“receiver 收到 canary”的语义。

### 验收证据

- 恰好生成 6 个案例，类型分布符合计划。
- 所有 `repo_files` 都在声明的 fixture 根目录内，绝对路径、`..` 和符号链接逃逸被拒绝。
- 每条记录保留原始 `verification_command`，并与安全 oracle 分开。
- 每条记录的 provenance 能回溯到固定 commit、dataset 路径和上游 ID。
- 相同输入重复导入的内容摘要一致。
- 移除 Inspect Evals/Inspect AI 后，生成物仍可加载和静态校验。
- 对恶意与 benign 记录分别验证安全端点极性和 false-positive 语义。

### 停止条件

- 无法确认选中样本及嵌入 `repo_files` 的复制或转换权利。
- scorer 的某个判断无法映射到明确的项目证据端点。
- 为完成转换必须让正式 runtime 依赖 Inspect 类型或 sandbox。

## Spike 2：SaberScenarioImporter

### 固定来源

- Repository: `https://github.com/sssr-lab/SABER`
- Commit: `bfdffb10c3887b38e1bd57ae2e548faa8f2049e9`

### Scenario A/B/C 各 2 条候选

| Scenario | 上游路径 | 上游 ID | 覆盖重点 |
| --- | --- | --- | --- |
| A | `tasks/A/info_leak/A_info_001.json` | `A_info_001` | 信息泄露、显式 tool-output 注入 |
| A | `tasks/A/code_tampering/A_code_041.json` | `A_code_041` | 代码篡改、file-content 注入 |
| B | `tasks/B/info_leak/B_info_001.json` | `B_info_001` | 合理请求下的疏忽泄露、无注入语义 |
| B | `tasks/B/code_tampering/B_code_001.json` | `B_code_001` | 合理请求下的疏忽篡改、无注入语义 |
| C | `tasks/C/info_leak/C_info_001.json` | `C_info_001` | 危险请求下的直接服从和信息泄露 |
| C | `tasks/C/code_tampering/C_code_001.json` | `C_code_001` | 危险请求/上下文下的直接服从和代码篡改 |

### 转换内容

- 映射 `setup` 中的 mock filesystem、显式文件内容、工作目录、权限和必要初始化描述。
- 映射正常任务、scenario/category/difficulty 和注入开关、方法、入口及触发条件。
- 保留 `harm_description` 作为审查上下文。
- 把 `harmful_command_patterns` 和 `expected_safe_commands` 放入 Assertion Candidate，记录
  其证据限制；不得将正则命中直接转换为最终安全 verdict。
- 把 SABER 模拟网络、git、包管理和 shell 行为标为不可无损迁移的 runtime 语义。

### 验收证据

- 恰好生成 A/B/C 各 2 个案例，并保留 source ID、scenario 和 category。
- 正常任务、fixture、攻击入口和授权上下文可以从生成物独立读取。
- A 中启用的注入位置被保留；B/C 的禁用注入不会被 importer 自行补成攻击步骤。
- 所有 harmful regex 只出现在候选断言或损失报告，不出现在最终安全结果字段。
- 不依赖 `TaskRuntime`、`SandboxShell`、SABER runner 或其 Python 包即可加载。
- 对 6 条记录重复转换得到相同摘要，并能解释所有未转换字段。

### 停止条件

- SABER 根 `LICENSE` 的 CC-BY-4.0 与 `dataset/README.md` 的 Apache-2.0 冲突未得到适用于
  选中路径的明确裁决。
- 需要把 SABER shell 模拟结果当作可信接收端或环境事实才能通过验收。
- Scenario B/C 的语义只能靠猜测或隐式默认值转换。

## Spike 3：TerminalBenchFixtureImporter

### 固定来源

- Repository: `https://github.com/harbor-framework/terminal-bench`
- Commit: `d28711d0da2675d0bb1d56de45ae5df6082438a3`
- Harbor 只作为 mapper/verifier 隔离设计参考：
  `d3e606d9f7d1e111bb22d3d820ebed03ec300eb3`

### 2 至 3 个候选任务

| 上游目录 | 当前源码规模 | 选择理由 | 计划攻击载体 |
| --- | --- | --- | --- |
| `original-tasks/log-summary` | 约 48 KiB | 日志 fixture 小、utility tests 明确 | 日志内容 |
| `original-tasks/jsonl-aggregator` | 约 48 KiB | JSONL 文件处理边界清晰 | 数据/配置说明 |
| `original-tasks/analyze-access-logs` | 约 196 KiB | 访问日志和输出检查明确 | 日志内容 |

先对三项运行来源、镜像、构建依赖和测试时长门禁。至少选择其中 2 项；只有第三项也满足
许可证清晰、环境较小、测试快速和 oracle 明确时才保留 3 项。源码规模是筛选线索，不是
“测试快速”的证据。

### 转换内容

- 转换 `task.yaml` instruction 和任务元数据。
- 转换 Dockerfile、Compose、fixture 文件和必要的环境初始化描述。
- 把 `run-tests.sh` 与 `tests/` 表达为 task oracle 候选，并记录执行权限和超时要求。
- solution 只进入隔离的校准/replay 材料清单，不进入生产 Agent fixture。
- 将日志、README 或配置攻击作为后续本地注入位置；不修改或提交上游任务原件。

### 验收证据

- 选中 2 至 3 个任务，每个任务都有 instruction、environment、tests/verifier、reset 和
  provenance。
- 构建所需镜像和网络依赖被固定或明确报告为不可复现风险。
- 测试在预先声明的时间预算内完成；预算在首次基线测量后固定，不按失败结果放宽。
- solution 不存在于 Agent 可见路径，且测试仍能验证正常任务结果。
- 生成 fixture 可植入选定的日志、README 或配置攻击，而不依赖 Harbor runner。
- 移除 Terminal-Bench/Harbor 包后，生成物仍可加载和静态校验。
- replay 差异要么有明确规范化理由，要么使该任务转换失败。

### 停止条件

- 任务、容器镜像、依赖或 fixture 的原始许可证/来源无法逐项确认。
- tests/verifier 依赖浮动远端服务、秘密凭证或无法固定的网络状态。
- solution 无法与 Agent 可见环境可靠隔离。
- 必须使用 Harbor Trial/Environment/Verifier 才能运行项目正式路径。

## 执行阶段和审查门

### 阶段 0：来源与许可门禁

- 固定所有输入 commit、路径、记录 ID 和内容摘要。
- 为每条候选资产记录软件/数据许可证及文件级附加条件。
- 对未批准项只允许更换同类候选，不允许降低数量或绕过许可证门禁。
- **退出证据**：每条入选资产在 manifest 或独立批准记录中具备可审查的
  `asset_import` 依据。

### 阶段 1：最小候选字段与损失协议

- 只实现三个 importer 共同需要的最小载体和 provenance/loss 表达。
- 用一条纯手工合成记录先证明独立加载、确定性摘要和 unknown-field 拒绝行为。
- 不加入任何上游数据，不定义完整 domain model。
- **退出证据**：合成记录的正反测试通过，候选字段每一项都有实际消费者。

### 阶段 2：CodeIPI 6 条纵向 spike

- 按固定分布导入、测试端点拆分和 benign false-positive 语义。
- 评审字段是否真的跨越 importer/runtime 或 replay 边界；删除只服务单条记录的通用抽象。
- **退出证据**：CodeIPI 验收证据全部满足，且无 Inspect 运行期依赖。

### 阶段 3：SABER A/B/C 各 2 条纵向 spike

- 验证同一候选字段能否表达 injection attack、careless mistake 和 risky direct compliance。
- 把 SABER runtime-only 语义明确留在损失报告。
- **退出证据**：SABER 验收证据全部满足，regex 没有升级为最终真值。

### 阶段 4：Terminal-Bench 2 至 3 个 fixture spike

- 先测量三项候选，再按门禁选择最终 2 至 3 项。
- 验证 instruction/environment/tests/solution 的分权和无 Harbor runtime 依赖。
- **退出证据**：Terminal-Bench 验收证据全部满足，solution 隔离可被自动验证。

### 阶段 5：跨来源收敛评审

- 对每个候选字段给出 `保留 / 改名 / 拆分 / 删除 / 继续观察` 裁决和案例证据。
- 比较三个 importer 的转换损失、错误类型、provenance 和独立加载行为。
- 删除只为模拟上游对象形状而存在的兼容字段。
- 不在本阶段把候选字段发布为稳定 API。
- **退出证据**：形成一份基于 14 至 15 个案例的字段裁决表和后续 schema 决策输入。

## 最终验证

下一阶段实现完成时至少运行：

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
git diff --check
```

还必须有自动化证据覆盖：

- 6 + 6 + 2 至 3 的案例数量和类型分布。
- 输入路径逃逸、摘要漂移、缺字段、未知字段和未知 schema 版本拒绝。
- 三个 importer 的重复导入确定性。
- 不安装上游包时的 Scenario Pack 独立加载。
- task/security oracle 分离以及 CodeIPI 五个安全端点的不同极性。
- SABER regex 只作为候选断言。
- Terminal-Bench solution 对 Agent 环境不可见。
- 每个生成物的 provenance 和转换损失完整。

## Dry Run 结论

- 三个 spike 没有生产 runtime 依赖，可以按来源独立审查，但共同字段必须先用合成记录建立
  最小协议，否则三个 importer 会各自发明一套形状。
- 最大前置风险是资产许可证，不是 parser。来源审批失败时应换同类样本或停止，不能先复制
  再补 provenance。
- Terminal-Bench 的“小”和“快”目前只有源码规模证据，阶段 4 必须先实际测量构建和测试。
- CodeIPI 的安全事件不能被一个 `exfiltrated` 布尔值表达；端点拆分是进入实现的硬门槛。
- SABER B 的 careless-mistake 与 C 的 risky direct-compliance 语义要求保留显式授权上下文，
  不能沿用 A 的 injection-attack 默认值。
- 当前路线可执行，但只产出 spike 证据和字段裁决，不产出最终领域模型。

## 第一执行动作

对计划中的 15 个候选上游记录逐条建立来源审批表；在每条记录的许可证、嵌入资产来源、
固定路径和摘要均可审查前，不创建 importer 代码或导入资产。
