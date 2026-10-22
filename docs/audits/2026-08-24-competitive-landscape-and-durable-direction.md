# Gawain 竞品格局与可持续产品方向

Date: 2026-08-24

Status: product-positioning recommendation; not an implementation claim

Evidence cut-off: 2026-08-24

## 1. 执行结论

Gawain 所在的市场不是空白市场。Aviator Verify、Shipmoor、
Evidence-First Harness 等产品已经在做「冻结意图、逐项验证、证据、硬判定」；
Roboticks、Saykai、SemaPLC 等产品也已经进入机器人或工业控制的验证领域。
因此，Gawain 不能再以「唯一的 AI 代码验证层」或「更好的多 Agent
Orchestrator」作为定位。

但这个市场还没有出现一个成熟产品，完整覆盖下面这条链路：

```text
human-approved Verification Contract
  -> harness-independent candidate
  -> build/deployment/device identity
  -> API + UI + backend + deployment + real-device execution
  -> causal, replayable evidence
  -> fail-closed verdict
  -> READY_FOR_HUMAN_ACCEPTANCE
```

Gawain 值得继续的唯一强方向是：

> **面向 AI 生成 cyber-physical systems 的跨 harness 独立验收运行时：
> 从冻结的人类意图一直证明到真实设备行为，并把可重放证据交给人类完成最终验收。**

这里的独特价值来自完整系统边界，而不是某一个 schema、prompt、skill、
trace 字段或 verifier Agent。单项功能几乎都已有竞品；完整组合仍有机会。

继续 Gawain 应当附带明确条件：停止与 Claude Code、Codex、DeepSeek Harness
竞争 task dispatch、session management、model routing 和自动修复；在一批真实任务中
证明它能发现「开发 harness 已经宣布完成、但真实系统验收仍会失败」的问题。

## 2. 本文区分的三种事实

为了避免把营销页当成产品事实，本文使用三层证据：

1. **公开可执行证据**：开源仓库、可安装包、真实测试、论文实验、公开用户案例。
2. **公开产品证据**：正式文档、CLI/API 合约、价格、变更记录；能够说明产品意图，
   但不等于已经被客户规模化使用。
3. **营销声明**：官网功能清单、私有 Beta、Request Access、非可执行示例；只证明
   团队正在表达这个方向。

成熟度评级：

| 等级 | 含义 |
|---|---|
| M3 | 已形成可验证的真实用户、稳定分发和持续维护 |
| M2 | 有可执行产品或开源实现，但产品或新功能仍处于早期 |
| M1 | Alpha/Beta/Pilot，主要证据来自文档、演示或小规模实现 |
| M0 | 概念或营销声明，缺少可执行证据 |

评级针对与 Gawain 重叠的具体产品能力，而不是母公司的总体成熟度。

## 3. Gawain 的目标边界

以下是产品方向，而不是对当前仓库能力的声明：

- 用户在开发或验收开始前审阅并冻结 `Verification Contract`。
- Claude Code、Codex、DeepSeek Harness 或其他开发工具负责设计、编码和修复。
- Gawain 不修改 candidate；失败后把结构化结果交回原开发 harness，产生新的
  candidate。
- 每一个接口和前端功能都要完成前端到后端的联合调试；必要时覆盖桌面端、部署端
  和真实设备。
- Gawain 可以调用真机，但真实设备操作必须绑定设备身份、部署身份、操作者许可、
  物理安全条件和原始证据。
- Gawain 的自动终态是 `READY_FOR_HUMAN_ACCEPTANCE`，不是替代用户签字的
  `ACCEPTED`。
- `full_access` 只允许绕过 Gawain 自己的软件门禁。硬件急停、机械限位、失联保护、
  现场安全员和设备原生安全控制必须始终保留。

当前实现与目标之间仍有明显距离。内部审计
[`2026-08-24-verifier-test-trace-audit.md`](2026-08-24-verifier-test-trace-audit.md)
已经确认：历史 Gawain 的主要能力是 Markdown 工作流、dispatch 和程序性 verifier；
candidate identity、可执行 test gate、因果 trace 和安全 evidence validation 才刚进入
第一批 P0 实现。本文不能被用来宣称目标能力已经交付。

## 4. 市场分层

### 4.1 直接竞品：AI 生成代码的独立验证

这一层已经证明需求存在，且与 Gawain 软件验证部分高度重叠。

| 产品 | 核心重叠 | 可见成熟度 | 主要缺口或边界 |
|---|---|---:|---|
| [Aviator Verify](https://www.aviator.co/verify) | intent、acceptance criteria、code scan、runtime scenario、criterion evidence、waiver、immutable audit、职责分离 | M2；Aviator 公司成熟，但 Verify 是 2026 年新产品 | 面向 GitHub PR 和软件 preview；未覆盖真实机器人、设备身份、现场 permit 和物理安全边界 |
| [Shipmoor](https://shipmoor.dev/) | frozen intent、atomic obligations、build/test/scan evidence、deterministic floor、VSA attestation、Claude/Codex/Cursor/Aider | M1；2026 年 Beta，公开仓库几乎无社区牵引 | 未覆盖真机和跨层部署身份；其 Agent Harness 也会参与 fix loop，独立性边界弱于 Gawain 目标 |
| [Evidence-First Harness](https://github.com/rmax-ai/evidence-first-harness) | untrusted patch、Evidence Bundle、versioned policy、deterministic decision、hash-chain provenance、mutation/adversarial checks | M1；2026-07 创建、0 star、Alpha，部分 evaluator 仍为 stub | 同一个 harness 内含 specification、implementation 和 repair；无真实设备验收 |
| [Validity](https://validity.ai/) | acceptance checklist、真实 UI、逐项 PASS/FAIL/could-not-verify | M1；invite-only Alpha | 自动 mock provider、auth 和 API，不能证明真实跨服务或真机闭环；强调 Agent 自验 |
| [Veriva](https://veriva.dev/) | AI PR 独立评分、agent attribution、policy merge gate、provenance、不自动修复 | M1；Request Access，无公开核心实现 | 更偏静态、安全和 PR 治理；没有完整 runtime behavior proof |
| [CodeVetter](https://codevetter.com/verification-evidence-bundle) | task/repo/base/attempt identity、命令和 artifact digest、fail-closed bundle、re-check linkage | M2 的个人工具，M1 的完整 verifier；公开仓库约 1 star | 自己的路线图明确承认真实 browser/app runtime evidence 和原始 intent loop 尚未闭合 |

#### 直接竞争判断

Aviator Verify 是最需要认真对待的直接竞品。它已经覆盖 Gawain 在纯软件领域的大部分
叙事：意图、逐条准则、运行时验证、证据、不可变审计和人工 waiver。Aviator 的母产品
也有既有企业客户和 SOC 2 能力。

不过，Verify 本身仍很新：Wayback 对 `/verify` 的首个可见快照在
[2026-06-08](https://web.archive.org/web/20260608013820/https://www.aviator.co/verify)，
公开客户案例主要属于 MergeQueue 等既有产品，而不是 Verify。其文档还说明 runtime
runner 使用 LLM，因此 runtime rerun 并非严格可复现，只能通过同 criterion/change-set
的 evidence cache 稳定结果。

Aviator 的标准流程通常是 Agent 完成实现后、PR 前提交 intent 和 acceptance criteria。
Gawain 如果要求「由用户在 candidate 产生前冻结 contract；contract 变更必然生成新版本
并使旧 evidence 失效」，可以形成更严格的防移动靶边界。但在实现和实测之前，这只是
差异化假设，不能当作既成优势。

Shipmoor 是概念上最接近的竞争者。它已经使用 obligations、deterministic floor、
content-addressed attestation、fail-closed、BYO judge 和跨 harness 等语言。Gawain 不应
花时间重新发明一个只验证普通代码 diff 的 Shipmoor。

### 4.2 机器人与工业系统验证

| 产品 | 核心重叠 | 可见成熟度 | 主要缺口或边界 |
|---|---|---:|---|
| [Roboticks](https://docs.roboticks.io/) | ROS2 requirement-to-test traceability、JUnit/MCAP、simulation runner、fault injection、PR gate、evidence pack、长期归档、标准映射 | M0–M1，营销与文档远领先于可执行证据 | 未围绕 AI coding candidate 或跨 harness；当前公开成熟度存在明显疑点 |
| [Saykai](https://saykai.com/) | versioned Safety Spec、Nav2 policy gate、deterministic pass/block、signed Safety Pack、shadow mode、人工 allowlist | M1；Private Beta/Pilot | 主要验证 Nav2 配置和部署前安全规则；尚未覆盖完整接口/UI/backend/真机验收 |
| [SemaPLC](https://github.com/midea-ai/SemaPLC) | project grounding、编译、部署到 live PLC runtime、变量 forcing、trace comparison、verification-gated completion | M2；有开源实现、论文和约 56 stars | PLC 专用；同一 harness 生成、诊断和修复，不是独立的通用验收方 |
| [ReSim](https://www.resim.ai/) | 自动驾驶/机器人仿真、回归测试、场景和大规模结果分析 | M3 的相邻平台 | 不负责 AI 任务意图、harness independence 或最终真机验收 |
| [Foretellix](https://www.foretellix.com/) | autonomy scenario-based V&V、覆盖率和安全验证 | M3 的相邻平台 | 偏自动驾驶安全验证平台；不是 AI coding acceptance runtime |
| [Formant](https://formant.io/)、[InOrbit](https://www.inorbit.ai/)、[Foxglove](https://foxglove.dev/) | fleet operations、teleoperation、logs、MCAP/visualization、现场 observability | M3 的相邻平台 | 观察和运营真实机器人，不从冻结意图产生独立 acceptance verdict |

Roboticks 在概念上是对 Gawain 机器人方向最强的挑战者，但截至证据截止日不能把它视为
成熟产品：文档声称 `pip install roboticks`，但 PyPI simple/JSON endpoint 返回 404；
文档链接的公开 `roboticks-runner` 仓库和 GitHub App 页面返回 404；安装文档仍含
`Screenshot needed` 占位；公开 GitHub 组织仅看到一个无 star 的 showcase 仓库；官网和
文档没有具名客户。它证明「有人在定义这个市场」，但尚不能证明已有成熟交付。

Saykai 对自身阶段表达更诚实：官网明确是 Private Beta/Pilot，公开 examples 也明确声明
是非可执行、字段和签名经过构造的示例。它值得持续关注，但现在不是已占领市场的产品。

SemaPLC 是目前最可信的工业动态验证信号。其论文和代码说明：静态分数相近时，部署到
live PLC runtime 后比较执行 trace 能显著拉开正确性差异。它直接支持 Gawain 的核心
判断——对 cyber-physical software，真实执行比静态 review 更有价值。

### 4.3 真设备执行层

[agent-device](https://github.com/callstack/agent-device) 是这一层最成熟、也最值得集成而
不是复制的产品。截至证据截止日，其公开仓库约 4,200 stars、260 forks，持续更新，
覆盖 iOS、Android、HarmonyOS、TV、Web、macOS、Linux、模拟器和物理设备；支持
accessibility snapshot、操作、截图、video、logs、traces、network data、replay、CI 和
device cloud，并列出 Expensify、Shopify 等使用信号。

它不冻结任务 contract、不绑定机器人部署身份、不产生整个任务的 fail-closed acceptance
verdict，也不管理现场安全许可。因此它不是 Gawain 核心层的替代品，而是理想的
`DeviceExecutionAdapter`。

### 4.4 可观测性、Agent eval 与供应链证明

| 类别 | 代表 | 与 Gawain 的关系 |
|---|---|---|
| Agent trace/eval | LangSmith、Braintrust、Arize Phoenix | 记录 LLM/Agent trajectory、数据集和 eval；不证明软件 candidate 在真实系统中满足用户 contract |
| Trace 标准 | OpenTelemetry、W3C Trace Context | 应作为 Gawain trace 的兼容基础，而不是自行创造不兼容 trace 生态 |
| 供应链证明 | in-toto、SLSA、Sigstore | 证明 artifact 从哪里来、由什么步骤构建；不证明其语义行为正确 |
| CI/Test | GitHub Actions、Buildkite、pytest、Playwright 等 | 作为 evidence producer；Gawain 不应重建 CI 或测试框架 |
| Robot evidence | MCAP、rosbag、simulator reports | 作为原始 evidence format；Gawain 负责绑定、验证、索引和 verdict |

这几个领域已经有成熟生态。Gawain 的正确选择是组合它们，而不是做另一个通用 trace
平台、CI 平台、artifact signer 或设备农场。

## 5. 核心能力矩阵

符号含义：`●` 公开能力较明确；`◐` 部分覆盖、领域受限或主要是程序性约束；`○` 未见；
`?` 主要来自营销声明，缺少公开可执行证据。

缩写：

- **HC**：跨 Claude/Codex/DeepSeek 等 harness
- **FC**：candidate 产生前冻结且版本化 contract
- **SEP**：verifier 与 fixer/implementer 强分离
- **ID**：candidate/build/deploy/device 连续身份链
- **DG**：deterministic、fail-closed gate
- **FS**：API/UI/backend/deployment 跨层动态验证
- **RD**：真实物理设备执行
- **RE**：因果、可重放 evidence
- **OP**：operator permit 与不可绕过硬件安全边界
- **HA**：显式最终人工验收

| 产品 | HC | FC | SEP | ID | DG | FS | RD | RE | OP | HA |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Gawain 当前实现 | ◐ | ○ | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | ◐ |
| **Gawain 目标边界** | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Aviator Verify | ● | ◐ | ● | ◐ | ◐ | ● | ○ | ◐ | ○ | ● |
| Shipmoor | ● | ● | ◐ | ◐ | ● | ◐ | ○ | ● | ○ | ◐ |
| Evidence-First Harness | ◐ | ◐ | ○ | ● | ● | ◐ | ○ | ● | ○ | ◐ |
| Validity | ● | ◐ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ○ | ◐ |
| Roboticks | ○ | ◐ | ◐ | ◐ | ? | ◐ | ◐ | ? | ○ | ◐ |
| Saykai | ○ | ● | ◐ | ◐ | ● | ◐ | ○ | ◐ | ◐ | ◐ |
| SemaPLC | ◐ | ◐ | ○ | ◐ | ● | ◐ | ◐ | ◐ | ○ | ○ |
| agent-device | ● | ○ | ○ | ◐ | ○ | ◐ | ● | ● | ○ | ○ |

矩阵表达的是产品边界，不代表 Gawain 已经领先。Gawain 目标行之所以看起来完整，正是
因为大部分格子还需要实现和真实任务证明。

## 6. 真正有价值且不与现有 harness 冲突的方向

### 6.1 独立验收，而不是独立开发

Gawain 的输入应该是：

```text
Verification Contract + Candidate Descriptor + Execution Permits
```

输出应该是：

```text
Evidence Bundle + Typed Verdict + Reproduction/Replay Instructions
```

Claude Code、Codex、DeepSeek Harness 等继续拥有：

- 对话与规划；
- repository exploration；
- 写代码和修改测试；
- model routing 和 subagent；
- 收到 Gawain 失败报告后的 repair loop。

Gawain 只拥有：

- contract version；
- candidate/build/deploy/device identity；
- required verification level；
- evidence provenance 与完整性；
- test/trace semantics；
- deterministic policy；
- waiver、permit、verdict 和 replay；
- human acceptance handoff。

这样每个 harness 都可以更强，而不会削弱 Gawain 的价值。

### 6.2 从代码身份延伸到现场身份

普通软件 verifier 通常只绑定 commit SHA。Cyber-physical acceptance 必须形成连续链：

```text
contract_version
  -> repository/base/tree/diff
  -> build artifact digest
  -> package/container/config digest
  -> deployment attempt and target
  -> device/robot/firmware/calibration identity
  -> test case and operator permit
  -> event/artifact/verdict
```

任意一环变化，旧 PASS 都不能自动继承。这个能力比再增加一个 AI reviewer 更难，也更
贴近真实现场价值。

### 6.3 跨层验收，禁止证据层级替代

Gawain 应明确区分：

```text
static
unit
component
integration
api_e2e
browser_e2e
desktop_e2e
deployment
real_device_e2e
```

Contract 要求什么层级，就必须观察到同一层级。代码阅读不能替代 API；browser mock
不能替代真实 backend；本机 backend 不能替代部署环境；simulation 不能静默替代真机。
允许替代时必须由人类明确修改 contract 或签署 waiver，不能由 verifier 自行降级。

### 6.4 因果 trace，而不是 Agent 对话日志

Gawain trace 的目标不是记录「Agent 想了什么」，而是重建：

- 哪个 contract claim；
- 对哪个 candidate/deployment/device；
- 由哪个 test case 和 attempt；
- 经过哪些服务和设备节点；
- 发送了什么输入；
- 观测到什么状态变化、失败和终态；
- 哪些 raw artifacts 支撑 verdict。

应兼容 W3C Trace Context/OpenTelemetry，并接收 MCAP、rosbag、JUnit、Playwright trace、
screenshots、device logs 等原始格式。Gawain 只定义跨格式的身份、因果和验收约束。

### 6.5 真实设备的双重授权模型

Gawain 的软件权限和现场物理权限必须分离：

```text
Gawain software gate        may be bypassed by full_access
Operator/device permit      always required when contract says so
Hardware safety interlocks  never disabled by Gawain
```

`full_access` 需要生成独立、可审计事件，至少包含人类授权者、范围、目标设备、原因、
开始/到期时间和被绕过的 Gawain gate。它不能更改急停、机械限位、watchdog、失联保护、
固件安全逻辑或现场安全员的权力。

这个边界既避免 Gawain 成为另一个权限沙箱，也避免把「全访问」误解成「无物理安全」。

### 6.6 最终状态是准备好由人验收

Gawain 不应自动宣称一个真实设备功能已经被业务接受。建议保留下列终态：

```text
FAIL
BLOCKED_INFRA
ENV_INVALID
INCONCLUSIVE
WAIVED
READY_FOR_HUMAN_ACCEPTANCE
```

用户查看 evidence、在真机上自行确认后，才产生独立的 human acceptance record。
这既符合责任边界，也比「AI 自己宣布完成」更适合安全敏感系统。

## 7. 应明确停止或降级的方向

Gawain 不应继续把以下能力作为产品核心：

1. 通用 task decomposition 和 dispatch。
2. Claude/Codex/DeepSeek session lifecycle、polling 和 context management。
3. model routing、prompt marketplace 或又一套 subagent framework。
4. 通用 AI code review、lint、SAST 或自动 fix-and-merge。
5. 重建 CI、pytest、Playwright、Appium、simulator、device farm 或 fleet platform。
6. 通用 LLM observability、token analytics 或 Agent trajectory dashboard。
7. 仅靠 Markdown 规则声称已经具有硬安全门禁。
8. 在缺少认证与独立审计时宣称满足 ISO、IEC、SOC 2 或机器人安全认证。

这些能力可以作为 adapter、evidence producer 或第三方集成存在，不能再次成为 Gawain
的差异化叙事。

## 8. 建议产品架构

```text
Developer Harnesses
Claude Code / Codex / DeepSeek / other agents
        |
        | candidate descriptor + failure feedback
        v
+-------------------------------------------------------+
| Gawain Verification Control Plane                     |
|                                                       |
| Contract Registry -> Identity Resolver -> Policy Gate |
|        |                 |                  |          |
|        +-------- Evidence Graph / Replay -------------+
+-------------------------------------------------------+
        |
        | adapter protocol
        v
CI / API / Browser / Desktop / Deployment / Simulator / Device
        |
        v
Evidence Bundle -> READY_FOR_HUMAN_ACCEPTANCE -> Human Sign-off
```

最小模块边界：

| 模块 | 职责 |
|---|---|
| Contract Registry | version、freeze、变更和 claim/test mapping |
| Candidate Resolver | repo、diff、build、deploy、device identity |
| Adapter Protocol | 调用既有测试、部署、浏览器、桌面和真机工具 |
| Evidence Validator | hash、path、schema、secret、environment、artifact completeness |
| Trace Validator | causal graph、span lifecycle、cross-run contamination、terminal event |
| Policy/Verdict Engine | closed required checks、fail-closed、waiver 和 typed verdict |
| Replay Package | 固定 candidate/environment/input，重现同一 test path |
| Human Acceptance | evidence review、现场确认、sign-off 与拒绝原因 |

## 9. 优先级建议

### P0：证明「不能假 PASS」

继续当前内部审计确定的三个 P0：

1. immutable candidate/evidence identity 和 hard verdict closure；
2. 拒绝零测试、少跑、ignored、错误层级和静态替代动态的 test gate；
3. versioned causal trace、terminal event、身份绑定和 secret blocking。

P0 完成标准不是 schema 文件存在，而是 adversarial tests 能稳定拒绝每一种 false-green
bundle。

### P1：证明跨 harness、跨层验收

选择少量 adapter，不建设大平台：

- 一个 CLI/CI adapter；
- 一个 API integration adapter；
- 一个 browser 或 Tauri desktop adapter；
- 一个现有真实设备/机器人 adapter。

同一个 contract 至少由两个不同开发 harness 产生 candidate，但 Gawain 使用同一验证
协议和 verdict 规则。

### P2：证明真实现场价值

- deploy/device/firmware/config/calibration identity；
- operator permit 与 `full_access` 审计；
- canary、timeout、loss-of-contact、rollback evidence；
- simulation-to-real 差异记录；
- `READY_FOR_HUMAN_ACCEPTANCE` evidence review 和最终人工记录。

## 10. 真正可能形成护城河的资产

不是护城河：

- JSON Schema；
- prompt 模板；
- verifier/fixer 两个 Agent；
- 一套 Markdown workflow；
- 「evidence-first」这个概念。

可能形成护城河：

1. **真实设备 adapter 与现场控制语义**：不同机器人、PLC、桌面和边缘设备的部署、
   复位、校准、状态和安全许可。
2. **失败语料**：开发 harness/CI 判定完成但真实 E2E 或真机失败的可重放案例。
3. **跨层 evidence graph**：从用户 claim 到代码、构建、部署、服务 trace 和设备状态的
   可靠映射。
4. **环境与身份解析**：知道「测试的究竟是不是将要交付的那一个 candidate」。
5. **replay reliability**：同一证据能够在新 verifier、事故复盘和人工验收时重建。
6. **现场验收流程**：operator permit、硬件安全保留、人工签字、waiver 和审计。
7. **真实基准**：能够量化减少了多少 false acceptance，而不仅是跑了多少 Agent。

## 11. 最大竞争风险

### 风险 A：Aviator 或 Shipmoor 增加设备 adapter

它们已经拥有 contract/evidence/verdict。如果增加 agent-device、SSH、ROS2 或 robot
cloud adapter，就会进入 Gawain 的右半段。

应对：优先积累真实设备身份、现场 permit、跨层因果和 replay 语料，而不是继续完善
通用 PR review。

### 风险 B：Roboticks 增加 coding-agent integration

Roboticks 的文档已经描述 requirement/test/evidence/compliance。如果其产品真正成熟，
再加 Claude/Codex MCP，就会从机器人侧向左扩张。

应对：保持 harness-neutral、支持非 ROS/非机器人目标，并把 candidate/deploy/device
identity 和人工验收做成开放协议。

### 风险 C：agent-device 增加 contract 和 verdict

agent-device 已有跨 harness、物理设备、evidence 和 replay。如果向上增加 acceptance
criteria、policy gate 和 human review，会成为移动/桌面领域的强替代。

应对：把 agent-device 当作 adapter，Gawain 专注跨软件服务、部署和机器人设备的统一
acceptance graph，而不是与其争夺设备控制命令。

### 风险 D：最强模型降低 verifier 的增量价值

SemaPLC 的实验已经显示，模型越强，harness 的部分优势会收窄。Gawain 不能把价值建立
在「再调用一个更聪明的模型」。

应对：价值必须来自外部可观察执行、身份绑定、fail-closed policy 和独立 human sign-off，
这些不会因为开发模型更强而自然消失。

## 12. 继续与停止条件

建议把 Gawain 作为有明确生死线的验证项目，而不是无限扩张的平台项目。

建议在一批真实任务上做基线对照：

```text
Baseline: development harness + existing CI + normal human spot-check
Treatment: same path + frozen contract + Gawain independent acceptance
```

至少衡量：

- blind external oracle 下的 false-accept / false-reject；
- 开发 harness 已宣布完成后，Gawain 发现的新增 P0/P1 缺陷；
- candidate/build/deploy/device identity coverage；
- raw-evidence completeness；
- required test 被零执行、ignored 或层级替代时的拒绝率；
- trace reconstruction 和 replay success；
- `READY_FOR_HUMAN_ACCEPTANCE` 后被用户拒绝的比例与原因；
- 每个 proven claim 的时间、设备占用和成本。

继续条件：在跨至少两个开发 harness、两个目标类型的真实任务中，稳定发现现有流程漏掉的
重要问题，并且 evidence 可以由另一 verifier 或人类重放。

停止或降级为内部协议的条件：

- Gawain 只重复已有 CI/测试结果，没有显著新增缺陷发现；
- 大多数 verdict 仍依赖 verifier 主观文字判断；
- 无法证明测试的是同一 candidate/deployment/device；
- 真机证据不可重放，用户仍需从头人工排查；
- 运行成本长期高于直接人工验收，且没有降低事故或返工；
- 产品重新滑回 dispatch/orchestration，核心能力可被任一 harness 原生功能替代。

## 13. 推荐定位与目标用户

推荐一句话定位：

> **Gawain independently proves that AI-built software behaves as agreed across
> services, deployments, and real devices before a human accepts it.**

中文：

> **Gawain 在人类最终验收前，独立证明 AI 构建的软件在接口、部署环境和真实设备上
> 确实按约定工作。**

首要目标用户：

- 已大量使用 Claude Code、Codex、DeepSeek 等工具开发的软件团队；
- 交付包含 API、前端/桌面、后端、部署和现场设备的完整路径；
- false acceptance 会造成现场返工、设备风险、客户停机或昂贵人工复测；
- 已有 CI、测试和设备工具，但缺少统一 contract、identity、evidence 和 acceptance。

不应优先服务：

- 只开发普通 Web CRUD、没有真实部署或设备验收要求的团队；
- 主要需求是多 Agent 调度或提升代码生成速度的团队；
- 希望 AI 自动修复、自动 merge、自动替代责任人的团队；
- 没有能力提供可测试环境、设备许可或人工最终验收的场景。

## 14. 研究限制

- 本文是截至 2026-08-24 的公开信息截面；这些新产品变化很快。
- 多数直接竞品没有公开、可归因到对应新产品的客户数据；官网功能不能视作规模化交付。
- Reddit 对 Shipmoor、Roboticks、Saykai 和 Evidence-First Harness 的精确搜索基本没有真实
  讨论；Twitter 因本地登录态不可用未能完成核验。缺少讨论只能说明未观察到社区信号，
  不能证明没有私有客户。
- Roboticks、Saykai 等产品的核心实现是私有的，因此成熟度判断主要依据公开可执行面、
  包分发、GitHub 状态、文档完整性和客户证据。
- 本文没有进行采购试用、付费 Pilot、真机对测或对竞品安全声明的独立审计。

## 15. 主要公开来源

- [Aviator Verify product](https://www.aviator.co/verify)
- [Aviator Verify documentation](https://docs.aviator.co/verify)
- [Aviator verification mechanics](https://docs.aviator.co/verify/concepts/how-verification-works)
- [Aviator audit trails](https://docs.aviator.co/verify/concepts/audit-trails-and-compliance)
- [Shipmoor product](https://shipmoor.dev/)
- [Shipmoor documentation](https://docs.shipmoor.dev/)
- [Evidence-First Harness](https://github.com/rmax-ai/evidence-first-harness)
- [Validity](https://validity.ai/)
- [Veriva](https://veriva.dev/)
- [CodeVetter](https://github.com/Codevetter/codevetter)
- [Roboticks documentation](https://docs.roboticks.io/)
- [Saykai product](https://saykai.com/product)
- [Saykai CI action](https://github.com/saykai-systems/saykai-action)
- [SemaPLC paper](https://arxiv.org/html/2608.18565)
- [SemaPLC repository](https://github.com/midea-ai/SemaPLC)
- [agent-device](https://github.com/callstack/agent-device)
- [ReSim](https://www.resim.ai/)
- [Foretellix](https://www.foretellix.com/)
- [Formant](https://formant.io/)
- [InOrbit](https://www.inorbit.ai/)
- [Foxglove](https://foxglove.dev/)

## 16. 最终产品决策

Gawain 应继续，但必须以验证核心为唯一主线：

```text
Stop: task dispatcher / general orchestrator / model router / autofix agent
Keep: adversarial verification insight and durable evidence discipline
Build: contract -> identity -> execution -> trace -> verdict -> human acceptance
Differentiate: cross-harness + cross-layer + real-device + physical-safety-preserving
Prove: lower false acceptance on real tasks, not more workflow complexity
```

如果能够证明这条链路，Gawain 不是另一个 skill 或插件，而是各类 harness 和测试工具
之上的独立验收边界。如果不能证明，它就应收缩为一套内部 verification protocol，而
不应继续扩张为独立平台。
