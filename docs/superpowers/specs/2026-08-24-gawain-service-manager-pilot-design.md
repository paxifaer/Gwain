# Gawain 独立验证运行时：Service Manager 真机 Pilot 设计

Date: 2026-08-24

Status: design approved in discussion; written specification awaiting user review

Target branch: `feat/verification-evidence-p0`

## 1. 决策摘要

Gawain 不再与 Claude Code、Codex、DeepSeek Harness 竞争任务分发、会话管理、
模型路由或自动修复。它的产品边界是一个 harness-neutral 的独立验证运行时：

```text
用户冻结 Verification Contract
  -> 开发 harness 产出 Candidate Set
  -> 操作员授予 Execution Permit
  -> Gawain 独立解析、部署、测试和采证
  -> fail-closed Verdict
  -> READY_FOR_HUMAN_ACCEPTANCE
  -> 用户真机验收
```

首个 Pilot 选择：

- 设备：`SP000065`；连接地址 `192.168.110.65`，地址不是设备身份；
- 服务：无执行器、导航和业务栈依赖的专用 user-systemd 单元
  `gawain-canary.service`；
- 生命周期服务 ID：`gawain-canary`；
- 动作：`Restart`；
- 用户路径：真实 Tauri 应用中的前端按钮，经现有 Tauri mTLS proxy command/IPC、
  lifecycle 专用接口、ArgoGateway、Backend 到真机 systemd，再由状态流返回前端；
- 自动成功终态：`READY_FOR_HUMAN_ACCEPTANCE`，不等于用户最终验收。

首轮不直接操作 `nav-runtime`。只有 canary Pilot 稳定后，第二阶段才用相同
Contract 模型验证 `nav-runtime`。

## 2. 为什么选择独立 canary

评估过三种方案：

1. **独立 `gawain-canary.service`（采用）**：仍然经过真实机器人、systemd、
   部署和业务控制链，同时能够确定性启动、失败和延迟，不把导航故障误判为
   Gawain 故障。
2. **直接重启 `nav-runtime`**：业务真实性更强，但会引入导航容器、ROS、配置、
   网络和机器人栈健康度等变量，首轮无法清楚归因。
3. **复用旧 `localization-robot-1-docker-exec` probe**：副作用低，但 SP000065
   已迁移为单一 `nav-runtime`，旧 probe 可能已经失真。

`Restart` 比单独 `Start` 或 `Stop` 更适合作为首个动作，因为它同时证明停止、
启动、过渡状态、最终状态和新进程实例；canary 又使这种覆盖不触碰执行器。

## 3. 目标和非目标

### 3.1 本 Pilot 必须证明

1. Gawain 能把用户批准的 Contract、独立解析的 Candidate Set 和操作员批准的
   Permit 绑定到同一个不可混淆的 run。
2. Gawain 能从真实 Tauri UI 动作验证到真机最终状态，再验证状态返回和前端
   最终呈现；低层 API 或静态检查不能替代缺失的高层证据。
3. Gawain 能识别“命令绿色但实验没执行”“ACK 成功但终态失败”“真实部署制品
   与候选不一致”和“trace 无法证明同一操作”等 false-green。
4. 正向和强制触发的负向场景都产生可重放、内容寻址的证据。
5. Gawain 不修改 Candidate；失败证据交回开发 harness，由后者产生新 Candidate。

### 3.2 本 Pilot 不做

- 不实现 task dispatch、Agent orchestration、model routing 或自动 repair loop；
- 不验证导航、运动控制或执行器行为；
- 不把浏览器 mock、直接 RPC、SSH 执行或静态源码检查当成完整 UI-to-device E2E；
- 不把 Gateway 的 `accepted=true` 当成生命周期成功；
- 不用 `full_access` 关闭急停、限位、watchdog、失联保护或现场安全流程；
- 不一次覆盖所有接口和前端功能。首个纵向切片证明方法成立后，再按接口/功能
  逐条建立 Contract。

## 4. 信任、身份与授权模型

### 4.1 三个独立输入

| 输入 | 信任来源 | 约束 |
|---|---|---|
| Verification Contract | 用户审阅并冻结 | Candidate 不能修改；任何修改生成新 `contract_id` 并使旧证据失效 |
| Candidate Descriptor | 开发 harness 提供，默认不可信 | Gawain 必须从仓库、制品和部署目标独立解析并比对 |
| Execution Permit | 操作员针对设备、动作、时窗签发 | 不能由 Candidate 或 Gawain 自动扩大范围 |

缺少任一输入都不能执行变更性真机步骤，也不能产生
`READY_FOR_HUMAN_ACCEPTANCE`。

### 4.2 Candidate Set

纵向链路可能跨 Gawain、前端、ArgoGateway 和 Backend 多个仓库，因此 Candidate
不是单个 `HEAD`。每个 component 至少绑定：

- repository identity 和 canonical path；
- base commit、HEAD commit、tree hash；
- dirty diff hash（干净时使用规定的空值）；
- build recipe identity；
- build artifact SHA-256；
- installed artifact SHA-256 和部署位置。

`candidate_id` 是规范化 component manifest 的 SHA-256。任一 component、diff、
build 或 installed digest 不一致，都在动作前 fail closed；不得用“HEAD 未变化”
替代脏工作树身份。

### 4.3 设备和环境身份

`SP000065` 是稳定设备身份；`192.168.110.65` 只是本次连接地址。环境快照至少包含：

- 设备身份和可验证的主机标识；
- Gateway mTLS endpoint `192.168.110.65:50053` 的端点与证书身份；
- canary unit 定义、scope、当前 unit digest 和状态；
- Backend、Gateway、Tauri 应用及相关配置的部署 digest；
- 系统时间、boot ID、systemd 版本和本次用到的安全控制状态；
- Contract 指定的依赖健康度。

IP 可记录为 `peer_addr`，但不能单独证明设备身份。

### 4.4 `full_access`

`full_access=false` 是默认值。`full_access=true` 只关闭 Gawain 自己的软件安全门禁，
例如动作 allowlist、变更速率限制和 Gawain 风险确认；它必须：

- 在 Permit、run、每个 mutation event 和最终 Verdict 中显式记录；
- 不伪造或替代用户 Contract、Candidate 身份、Execution Permit；
- 不放松证据完整性、测试层级、trace、digest 或 Verdict 规则；
- 不关闭真机急停、机械/电气限位、watchdog、失联保护和现场安全员权限。

即使现场有安全员，硬件原生安全边界也始终有效。

## 5. 精确 Verification Contract

### 5.1 固定目标

```yaml
contract_kind: service-manager-vertical-e2e
device_id: SP000065
connection_hint: 192.168.110.65
gateway_endpoint: 192.168.110.65:50053
service_id: gawain-canary
unit: gawain-canary.service
systemd_scope: user
action: Restart
success_terminal: READY_FOR_HUMAN_ACCEPTANCE
```

真实 Contract 使用版本化、规范化的机器可读格式，并由内容摘要生成
`contract_id`。上面的 YAML 只表达被冻结的语义，不是最终 schema 承诺。

### 5.2 canary 行为边界

canary 必须满足：

- 不访问执行器、导航、ROS graph 或机器人业务端口；
- 不需要 root 常驻权限；
- 启动时产生唯一 generation，并把 generation、PID、boot ID、启动单调时间和
  自身 artifact digest 写入结构化日志或只读状态出口；
- 正常模式保持 `active/running`；
- 仅通过 Permit 约束的 fixture 配置支持“启动失败”和“延迟 ready”两种故障注入；
- 每次注入可撤销，恢复后能证明 unit definition 和 fixture digest 回到基线。

PID 变化只是辅助 oracle，因为 PID 可能复用。generation 变化、systemd
`ActiveEnterTimestampMonotonic` 增长和已绑定的 artifact digest 才是主 oracle。

### 5.3 正向场景的必要判据

一次正向 Restart 只有同时满足以下条件才成立：

1. Gawain 在点击前记录 canary 为 `active`，以及 generation、MainPID、
   ActiveEnterTimestampMonotonic 和 digest 基线。
2. 动作从真实 Tauri 应用的目标前端控件发起；需要 renderer 与 Tauri host
   身份证据。只调用 `runLifecycleExecute` 或直接 RPC 不满足这一条。
3. 同一个 `operation_id`/W3C `trace_id` 贯穿 renderer、Tauri 边界、Gateway、
   Backend、systemd adapter、状态发布和前端终态呈现。
4. Gateway 的同步响应 `accepted=true` 只记为 provisional ACK，不改变最终成功状态。
5. Backend 产生与该 operation 绑定的 terminal lifecycle result；仅有周期性状态
   快照不能冒充命令结果。
6. Restart 后 generation 改变、启动单调时间增长、unit 为 `active`，且部署 digest
   仍与 Candidate Set 一致。
7. 返回的 lifecycle state 与同一 operation 绑定，`phase=Running` 且
   `converged=true`。
8. 前端只能在上述 terminal result 到达后显示最终 `Running`；ACK 到达时最多显示
   “已受理/进行中”。
9. 必需测试记录的 expected count 与 executed count 相等，ignored 为零，exit code
   为零，且没有层级替代。
10. 所有必要 evidence 均存在、SHA-256 匹配且 trace 拓扑有效。

现有实现中 `LifecycleExecute` 虽带 `request_id`，但 Gateway 发布给 Backend 的负载
只有 `op` 和 `service_id`；状态事件也不能证明属于哪个命令。因此当前代码不能满足
第 3、5、7 条。Pilot 必须把这个差距作为待实现条件，不能用时间邻近推断关联。

### 5.4 Tauri 边界的诚实定义

SP000065 使用 `https://192.168.110.65:50053`。现有 gateway transport 会把这类
allowlisted LAN mTLS 请求转入 Tauri 的 `gateway_mtls_proxy`，状态订阅则经过
`gateway_mtls_proxy_stream`，所以目标路径已经真实穿过 Tauri Rust IPC，不需要再新增
一个 lifecycle 专用 Tauri command。Pilot 要补的是这些现有 IPC 的 W3C client/server
spans，并证明 unary 请求和 streaming 状态回流都走过 Tauri。普通浏览器、plaintext
或关闭 mTLS proxy 的开发模式只能作为低层诊断，不能满足 P-01，也不得生成假的 Tauri
span。

## 6. 必需测试矩阵

| ID | 场景 | 强制 oracle | 场景结果 |
|---|---|---|---|
| P-01 | 正常 Restart | §5.3 全部成立 | `PROVEN` |
| N-01 | namespace/service ID 错误 | 请求被拒绝或终态明确失败；真实 canary generation 不变；UI 不显示成功 | `EXPECTED_REJECT` |
| N-02 | Gateway ACK 丢失 | 不因超时盲目重试非幂等 Restart；实际设备状态与 UI/Backend 分歧被明确报告 | `EXPECTED_REJECT` |
| N-03 | canary 故意启动失败 | systemd failed、Backend terminal failure、前端 failure 三者关联；绝不显示 Running | `EXPECTED_REJECT` |
| N-04 | ready 超过 Contract timeout | timeout 被归因到正确 span；迟到状态不能把已结束 attempt 静默改绿 | `EXPECTED_REJECT` |
| N-05 | installed artifact digest 陈旧 | 动作前拒绝，真机 generation 不变 | `EXPECTED_REJECT` |

负向测试不是“测试失败”。只有预期拒绝行为和无错误副作用都被证明时，case 才记为
`EXPECTED_REJECT`。注入没有实际生效、证据缺失或观察层级错误时，不能记为通过。

建议执行顺序是 N-05、P-01、N-01、N-02、N-03、N-04，随后恢复基线并执行一次
只读健康确认。每个注入都有 setup digest、激活证据、cleanup digest 和 cleanup
oracle；前一个 cleanup 未证明，后一个 case 不得开始。

## 7. 运行阶段和数据流

```text
Resolve Contract/Candidate/Permit
  -> Read-only preflight and environment snapshot
  -> Prepare rollback and canary fixture
  -> Start evidence capture
  -> Execute test matrix through real Tauri UI
  -> Independently query device/systemd oracles
  -> Close and validate traces
  -> Hash and seal evidence bundle
  -> Deterministic verdict
  -> Keep deployment for human acceptance OR rollback
```

关键分离：

- **控制面 trace**：Gawain 的 preflight、部署、注入、恢复、采证和判定；
- **应用面 trace**：用户动作在 renderer/Tauri/Gateway/Backend/真机/状态返回中的因果链；
- **独立 oracle**：Gawain 直接读取 systemd 和 canary 状态，不能只相信被测应用自报。

应用面与控制面通过 `run_id`、`test_case_id`、`attempt_id`、`operation_id` 和
artifact references 关联，但不能把 Gawain 自己的控制日志冒充应用行为证据。

## 8. Trace 合约

trace 采用版本化 JSONL，兼容 W3C Trace Context / OpenTelemetry 的身份模型：

- 128-bit、32 个小写十六进制字符的非零 `trace_id`；
- 64-bit、16 个小写十六进制字符的非零 `span_id`；
- 除唯一 root 外，每个 span 都有存在的 `parent_span_id`；
- 每个 span 恰好一个 start 和一个 terminal end；
- event identity 在 run 内唯一，并带单调 `sequence`；
- 每个事件绑定 schema version、run、candidate、contract、test case、attempt、
  operation、service instance 和可选 device identity。

P-01 至少需要以下逻辑 spans：

```text
gawain.test_case
  -> frontend.renderer.action
     -> tauri.gateway_mtls_proxy
        -> argogateway.lifecycle_execute
           -> backend.lifecycle_control
              -> systemd.restart
              -> backend.lifecycle_terminal
           -> argogateway.lifecycle_state
        -> frontend.render_terminal_state
```

验证器拒绝：缺父 span、重复 identity、跨 candidate/run/test 污染、缺 terminal、
operation 不连续、凭时间猜测父子关系，以及含敏感字段或私钥材料的 evidence。

## 9. Evidence Bundle

每个 run 形成只追加、内容寻址的 bundle，最少包含：

```text
bundle/
  contract/
  candidate/
  permit/
  environment/
  deployment/
  tests/
  traces/control-plane.jsonl
  traces/application.jsonl
  artifacts/
  verdict.json
  human-acceptance.json       # 自动运行结束时可不存在
  manifest.json
```

`manifest.json` 记录每个文件的相对安全路径、媒体类型、字节数和 SHA-256；manifest
自身摘要形成 `bundle_id`。拒绝绝对路径、`..`、symlink escape、缺文件、重复 artifact
ID、hash 不匹配和未知 evidence reference。

关键 artifacts 包括：

- Contract、Candidate Set 和 Permit 的规范化内容与摘要；
- pre/post systemd properties、canary generation 和 unit journal；
- Gateway、Backend、Tauri host、renderer 的结构化日志；
- 实际 Tauri 交互记录以及关键 UI 状态截图/视频；
- 每个测试的命令/driver、环境、expected/executed/ignored count、exit code 和 oracle；
- 故障注入和 cleanup 的前后 digest；
- installed artifact 的独立 hash 读取结果；
- deterministic verdict reasons。

截图只能证明呈现，不能单独证明 Backend 或设备行为；日志也不能单独证明用户看到的
终态。每条 claim 必须引用与其层级相符的 evidence。

## 10. Verdict 与恢复语义

只允许以下自动终态：

| Verdict | 含义 |
|---|---|
| `FAIL` | Candidate 行为与冻结 Contract 冲突，且证据足以归因 |
| `INCONCLUSIVE` | 实验执行了，但必要证据缺失、矛盾或无法建立因果关系 |
| `BLOCKED_INFRA` | 外部基础设施阻止实验开始或继续，不能归咎 Candidate |
| `ENV_INVALID` | preflight、身份、digest、安全条件或 fixture 基线不满足 Contract |
| `ABORTED` | 操作员、急停、安全系统或运行时主动终止 |
| `READY_FOR_HUMAN_ACCEPTANCE` | 所有正向和负向 obligations 被证明，可交用户真机验收 |

不存在自动 `PASS` 或 `ACCEPTED`。waiver 是单独的人类对象，不能把 FAIL 改写成
READY；它必须包含作者、范围、理由、policy version 和 expiry。

恢复规则：

- `READY_FOR_HUMAN_ACCEPTANCE`：保留已验证 Candidate 和正常 canary 状态，供用户
  真机验收；保存 pre-run snapshot 直到用户决定结束。
- `FAIL`、`INCONCLUSIVE`、`ENV_INVALID`：默认恢复到 pre-run 部署和 fixture 状态，
  并验证 rollback digest。
- `BLOCKED_INFRA`：若尚未 mutation 则不动作；若已 mutation 则默认 rollback。
- `ABORTED`：立即停止新动作，优先服从硬件/现场安全控制，再做允许范围内的恢复。
- rollback 失败不会覆盖原 Verdict；附加 `rollback_status=FAILED` 并升级人工处置。

## 11. 三个 P0 的实现边界

Pilot 驱动的首批 P0 是三个彼此独立但串联的最小核心：

1. **Identity and authorization gate**：冻结 Contract；解析多仓 Candidate Set；验证
   deployed digest、Permit、设备身份和 `full_access` 语义。
2. **Executable test and oracle gate**：机器可读 test record；严格 count/layer/oracle；
   正向与 force-trigger 负向测试；真实 Tauri/部署/真机层不能被低层替代。
3. **Causal evidence and verdict gate**：W3C/OTel 兼容 trace、内容寻址 artifacts、
   secret rejection、封闭 Verdict 状态机和 rollback/hand-off 记录。

这三个核心只消费外部 harness 产出的 Candidate，并输出结构化 evidence/verdict。
它们不包含任务调度或代码修改能力。

## 12. 实现前验收清单

实施计划必须把以下事实转为可失败的自动测试：

- 修改 Contract、任一 component/diff/build/deploy digest 会阻止动作；
- 缺 Permit 或设备身份不匹配时，即使 `full_access=true` 也不能产生 READY；
- zero tests、count shortfall、ignored required test、非零退出、layer substitution、
  缺失动态证据都会被拒绝；
- ACK-only、周期状态快照和时间邻近不能证明 Restart 成功；
- operation/trace 在任一 hop 丢失会得到 INCONCLUSIVE 或 FAIL，而不是 READY；
- 五个负向场景均能强制触发，并证明注入实际生效和 cleanup 完成；
- 成功保留部署供用户验收，失败按规则回滚；
- Gawain 没有修改 Candidate，也没有越过 Permit 控制的设备/动作/时窗；
- 最终用户可以在 SP000065 上独立复核 canary 当前 generation、unit 状态、部署
  digest 和对应 bundle。

## 13. Pilot 之后

canary Pilot 通过且用户完成真机验收后，第二个 Contract 使用相同框架验证
`nav-runtime`。它是新的高风险 Contract，需要独立 Permit、业务健康 oracle、回滚
策略和现场步骤，不能因 canary READY 自动继承授权。

随后按“一个接口或一个前端功能 = 一个冻结 Contract + 一条真实纵向路径”的方式扩展
覆盖率。覆盖率按 obligations、真实层级和可重放证据计算，不按测试文件数量或 Agent
声称完成的任务数计算。
