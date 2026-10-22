# Lifecycle Unified API — Design Doc

- **Author**: design worker (kimi-k3, ~30 min)
- **Status**: DRAFT for orchestrator review
- **HEAD reference**: ArgoWatch `d2b3b9d` / robot-app-platform `4b5b27e2`
- **Write-set**: 仅此一个文件,0 src 修改,0 git 操作

---

## 1. Background & motivation

### 1.1 现状(来自源码)

当前 lifecycle 共有 7 个 action,每个 action 对应一个独立 zenoh topic:

| Verb | Action string | Zenoh topic | Payload 关键字段 | 处理器位置 |
|---|---|---|---|---|
| list_groups | `lifecycle.list_groups` | `/{f}/{b}/watch/lifecycle/list_groups/submit` | (无) | `demo-app-lifecycle/src/handlers.rs:412` |
| list_state | `lifecycle.list_state` | `/{f}/{b}/watch/lifecycle/list_state/submit` | (无) | `handlers.rs:390` |
| get_state | `lifecycle.get_state` | `/{f}/{b}/watch/lifecycle/get_state/submit` | `service_id` | `handlers.rs:365` |
| start | `lifecycle.start` | `/{f}/{b}/watch/lifecycle/start/submit` | `service_id`,`requested_by` | `handlers.rs:181` |
| stop | `lifecycle.stop` | `/{f}/{b}/watch/lifecycle/stop/submit` | `service_id`,`requested_by` | `handlers.rs:202` |
| restart | `lifecycle.restart` | `/{f}/{b}/watch/lifecycle/restart/submit` | `service_id`,`requested_by` | `handlers.rs:250`(D-115 级联) |
| group_restart | `lifecycle.group_restart` | `/{f}/{b}/watch/lifecycle/group_restart/submit` | `group_id`,`requested_by` | `handlers.rs:683` |

Action 常量在 `demo-app-lifecycle/src/handlers.rs:33-41`;dispatcher 在 `demo-app-backend/src/handlers.rs:374-460`,靠 topic 解析出的字符串做 `match`(`extract_action_from_topic` 见 `demo-app-backend/src/topic.rs:12-26`)。

### 1.2 问题

每加一个新 op(health_check / snapshot / rollback / scale / ...)就要:
- 新增一个 zenoh topic 订阅;
- 在 `dispatch_action` 增加一个 match 分支;
- 在前端 `demoRobotControl.ts` 写一个新的 wrapper;
- 每加一种 target kind(container/process/unit/...)就要再开一组 topic/分支。

用户明确要求:**不再"一 op 一 topic / 一 op 一 RPC"**。

### 1.3 两个新增硬约束(用户后续补充)

- **C1 兼容性**:字段/功能会扩充 → proto 设计必须向前/向后兼容(老 client + 新 backend、新 client + 老 backend 都要能跑)。
- **C2 消息总线 = ArgoDDS + ArgoGateway server**,必须给端到端测试计划,链路:
  `Frontend → (Connect-RPC / HTTP) → ArgoGateway server → (zenoh pub) → ArgoDDS → (zenoh sub) → demo-app-backend → demo-app-lifecycle → provider`。

---

## 2. Current state(逐文件读源码得到)

### 2.1 Envelope(请求/响应外壳)

`demo-app-lifecycle/src/envelope.rs:9-105`,与 backend `envelope.rs` 字节一致:

```rust
pub struct Header {
    pub id: String,                          // UUID v4
    pub ref_id: Option<String>,              // response → request.id
    pub action: String,                      // 如 "lifecycle.start"
    pub direction: Direction,                // Request / Response
    pub status: Status,                      // Ok / Error / Pending / Partial
    pub timestamp: String,                   // RFC3339 millis
    pub version: String,                     // "1.0"
}

pub struct Envelope {
    pub header: Header,
    pub payload: serde_json::Value,          // 任意 JSON
    pub error: Option<ErrorDetail>,          // { code, message }
}
```

**关键**:Envelope 本身已经是一个"通用 envelope + payload"模型,后端 7 个 lifecycle handler 全部走这个 envelope,**这正是统一 API 的天然底座** — 不需要推翻 Envelope,只需要引入"单 action + 内部 op 判别"即可。

### 2.2 错误模型(已是字符串 enum)

每个 handler 返回 `Envelope::error_response(req, code, message)`,现有 code 全集(来自 handlers.rs 实际调用点):

| code | 出现位置 | 触发场景 | byte-exact message 模板 |
|---|---|---|---|
| `INVALID_INTENT` | handlers.rs:197, 218, 267 | §5.4 phase 矩阵拒绝 | `op {Op:?} is not allowed while service '{sid}' is in phase {Phase:?} (arch doc §5.4 matrix)` |
| `MISSING_FEATURE` | handlers.rs:717-723 | group 成员未 expose lifecycle | `service '{sid}' in group '{gid}' does not expose Feature::Lifecycle; group verb refuses to actuate it` |
| `UNKNOWN_SERVICE` | handlers.rs:373-376 | service_id 不在 registry | `unknown service id '{sid}'` |
| `UNKNOWN_GROUP` | handlers.rs:694-698 | group_id 不在 registry | `unknown group id '{gid}'` |
| `NO_STATE` | handlers.rs:380-385 | service 在 registry 但无 state 快照 | `service '{sid}' has no state yet` |
| `BAD_PAYLOAD` | handlers.rs:369 | service_id 字段缺失/非 string | `payload missing required field 'service_id' (string)` |
| `MISSING_FIELD` | handlers.rs:687-691 | group_id 缺失 | `payload missing required field '{field}' (string)` |
| `EMPTY_GROUP` | handlers.rs:703-709 | group 无 computed_members | `group '{gid}' has zero computed_members; nothing to restart` |
| `TOPO_CYCLE` | handlers.rs:728-730 | depends_on 成环(defensive) | `depends_on cycle detected inside fan-out closure ...` |
| `GROUP_MEMBER_STOP_FAILED` | handlers.rs:749-753 | group stop leg 写失败 | `stop write for group member '{sid}' failed: {cause}` |
| `GROUP_MEMBER_START_FAILED` | handlers.rs:784-788 | group start leg 写失败 | `start write for group member '{sid}' failed: {cause}` |
| `UNKNOWN_ACTION` | backend handlers.rs:455-457 | dispatch 失败兜底 | `unknown action: {action}` |
| `BAD_ENVELOPE_BRIDGE` | backend handlers.rs:410, 440 | envelope 桥接失败 | `failed to bridge envelope to lifecycle: {e}` |

§5.4 相位合法性矩阵在 `handlers.rs:53-69`(以代码注释形式记录,即"arch doc §5.4"指的就是这块):
- `Start` 允许相位:`Pending | Stopped | Failed`
- `Stop` 允许相位:`Starting | Running | Degraded | Failed`
- `Restart` 允许相位:`Running | Degraded | Stopped | Failed | Completed`(P4/V3-C1 加入 Completed 以匹配 oneshot 重触发)

### 2.3 Registry(SP000065 实际部署版)

`demo-app-lifecycle/examples/registry-sp000065.yaml`(P5 dogfood 用,边界=只读 status 居多):

| group | service_id | expose | provider | selector |
|---|---|---|---|---|
| robot-comm | `argo-zenoh-global` | [status] | systemd system | `argo-zenoh-global.service` |
| robot-stack-members | `localization-robot-1-docker-exec` | **[lifecycle, status]** | docker exec_process | `container=localization-robot-1, exec_process=p5-probe, exec_start="echo PA3_OK && id && hostname"` |
| robot-stack-members | `rustbot-daemon-http` | [status] | http roboctl-pool | `GET /api/units` |
| robot-oneshot | `ethercat-oneshot` | [status] | systemd system | `ethercat.service` |
| robot-stack | `rustbot-daemon-member` | [status] | systemd system | `rustbot-daemon.service` |
| robot-stack | `rustbot-monitor-member` | [status] | systemd system | `rustbot-monitor.service`,depends_on=[daemon] |
| robot-stack | `localization-member` | [status] | docker | `container=localization-robot-1` |
| robot-stack | `nav2-member` | [status] | docker | `container=nav2-dev` |

→ **8 个 service,4 个 group,3 类 provider(systemd / docker / http-roboctl-pool)**,与 prompt 一致。唯一暴露 `lifecycle` 的是 `localization-robot-1-docker-exec`(PA3 dogfood 探针),它是 e2e 测试 start/restart 的合法目标。

`registry-robot.yaml` 是**未来形态**清单(18 svc / 5 group),目前不部署,但揭示了目标扩展性:同一份统一 API 必须支持 systemd unit、docker container、docker exec_process、http probe 这 4 种 provider shape。

### 2.4 Dispatch path(backend → lifecycle 库)

`demo-app-backend/src/handlers.rs:374-460`:

1. `extract_action_from_topic(topic)` 把 `/{f}/{b}/watch/lifecycle/start/submit` → 字符串 `"lifecycle.start"`(topic.rs:12);
2. 字符串装入 `Envelope.header.action`;
3. `dispatch_action` 用 `match envelope.header.action.as_str()` 做字符串匹配,匹配到 7 个.lifecycle 常量后,通过 `to_lifecycle_env`(serde_json round-trip)桥到 lifecycle 库 envelope;
4. 再按字符串二次 `match` 调用对应的 `handle_lifecycle_*` 函数(handlers.rs:415-426)。

**关键发现**:dispatch 是字符串驱动的——新增一个 `lifecycle.execute` action 只需要:
- 一个新常量 `ACTION_LIFECYCLE_EXECUTE = "lifecycle.execute"`;
- `dispatch_action` 加一个分支,调 `handle_lifecycle_execute`;
- `handle_lifecycle_execute` 内部根据 `payload.op` 字段二次分发到现有 7 个 handler(复用,不重复代码)。

→ 后端 spawning 一个统一 op 的边际成本就一个新 match 分支 + 一个 dispatcher 函数,不再是 "7 topic × 7 RPC" 的乘法式增长。

### 2.5 前端 → ArgoGateway → ArgoDDS 链路(已存在)

`frontend/robot-app-platform/packages/gateway-client/src/lib/demoRobotControl.ts:239-258`:

```typescript
async function runChatCommand(input: ChatCommandInput) {
  const client = getGatewayRobotControlConnectClient(input.session.gatewayBaseUrl);
  const response = await client.chat(create(ChatRequestSchema, {
    botName: input.session.botName,
    command: `watch/${input.action.replace(/\./g, "/")}/submit`,  // ★ 通用隧道
    fleetId: input.session.fleetId,
    payload: JSON.stringify(input.payload ?? {}),
    requestId: createRequestId(),
    streaming: true,
    timeoutMs: BigInt(input.timeoutMs ?? 10_000),
  }));
  requireChatOk(response, input.action);
  return response;
}
```

当前 lifecycle 是通过 `Chat` RPC 通用隧道调 lifecycle 的(`restart_service / start_service / stop_service` 也是这条路径,demoRobotControl.ts:356-378)。**Chat RPC 已经能干所有事** — ArgoGateway 收到 `command = "watch/<verb>/submit"` 后会 zenoh publish 到 `/{fleet}/{bot}/watch/<verb>/submit`,并把订阅到的 result 包装为 `ChatResponse` 返回。

`FrontendRobotControlService` 已有 11 个 RPC(robot_control_pb.ts:1534-1658),`Chat` 是其中之一。若沿用 Chat,**新增 unified lifecycle 不需要改 ArgoGateway proto**;若走 typed RPC,则需要在 `robot_control.proto` 加 `LifecycleExecute` 方法 + 消息类型 → 触发 frontend/backend buf generate。§4 给出取舍。

### 2.6 ArgoDDS zenoh topic 模式

约定(见 `topic.rs:1-44` 与引用文档 `docs/argo/argo-data-bus-ai-reference.md`):
- 命令通道:`/{fleet_id}/{bot_name}/watch/{action}/submit`(pub/sub)
- 响应通道:`/{fleet_id}/{bot_name}/watch/{action}/result`(由 `infer_reply_topic_for_submit` 推导,`submit→result`)
- task 通道:`/{f}/{b}/task/submit` / `/task/status`

模型是 **pub/sub + 双 topic 关联**(request/response 用 `ref_id` 匹配),不是 zenoh queryable。理由(可推断):pub/sub 与 audit/event 流同构,易持久化、可多 subscriber 旁听(audit、logger、UI)。统一 API 沿用此模型,不引入 queryable。

---

## 3. Design goals

1. **单 topic、单 action**:`/{f}/{b}/watch/lifecycle/execute/submit`,取代 7 个 verb topic(对外)。
2. **单 envelope、op 作为 payload 字段**:继续用现有 Envelope;`payload.op` 决定具体动作,`payload.params` 携带该 op 的参数。
3. **新增 op 零新增 topic/RPC**:加 `HealthCheck` = 加枚举值 + 加 handler + 加 UI 调;proto/topic/RPC 不动。
4. **新增 target kind 同理**:`target = {kind, id}`,kind 是可扩展枚举,不需要重新规定 schema 形状(配合 SVC-level 强类型参数)。
5. **字节级契约保持**:`INVALID_INTENT` / `MISSING_FEATURE` 等错误 code 与 byte-exact message 必须与现有 §5.4/§preknown 完全一致(E2E 用正则/字符串比对验收)。
6. **C1 兼容性**:proto3 + oneof + reserved field number / enum value / optional 规则确保老新兼容。
7. **C2 端到端可测**:每一跳都可独立 mock + 真机 SP000065 全链路验证;新增 op 的 E2E 成本 = 加一个 case,不加 topic / RPC / 信道。

---

## 4. Proposed design

### 4.1 总体形态

- **Zenoh topic(单、固定)**:`/{fleet_id}/{bot_name}/watch/lifecycle/execute/submit`(响应:`.../result`)
- **Action 字符串(单)**:`lifecycle.execute`
- **Frontend → ArgoGateway RPC**:**两种方案,推荐 A(短期) + B(长期)**
  - **方案 A(短期,0 proto 改动)**:继续复用 `Chat` RPC(`robot_control_pb.ts:1639-1643`),命令字符串变成 `watch/lifecycle/execute/submit`,`payload` 字段装 unified JSON request。
  - **方案 B(长期,推荐落地目标)**:在 `FrontendRobotControlService` 新增 typed RPC `LifecycleExecute(LifecycleRequest) returns LifecycleResponse`,ArgoGateway 内部仍然 publish 同一个 zenoh topic。
  - §4.7 给出选型。

### 4.2 LifecycleRequest(unified payload schema)

**载体选择**:鉴于现有 Envelope 已经传 `payload: serde_json::Value`,**当前实现可以纯 JSON,无需 proto**。但用户已明示"我们会扩充字段和功能"+"消息总线就是 ArgoDDS + ArgoGateway",为类型安全 + 代码生成 + 兼容性规则落地,本节按 **protobuf schema** 写,序列化格式见 §5.6 推荐。

```proto
syntax = "proto3";
package gateway.v1.lifecycle;

// ═══════════════════════════════════════════════════════════════
// LifecycleRequest — unified op wrapper
// ═══════════════════════════════════════════════════════════════
message LifecycleRequest {
  // ─── 刚性协议字段(永远保留,编号 1-9 预留)─────────────────────────
  string         request_id        = 1;   // UUID v4,与 Envelope.header.id 一致
  string         fleet_id          = 2;
  string         bot_name          = 3;
  optional uint32 timeout_secs     = 4;   // optional: 0/unset = backend default
  optional uint32 schema_version   = 5;   // 见 §5.4,当前 = 1
  optional ClientCaps client_caps  = 6;   // 见 §5.5,可空
  string         requested_by      = 7;   // 现有 handler 已支持,PROMPT-W2 §6

  // ─── op oneof:每个 op 一个分支 ──────────────────────────────────
  // 编号约定:10-49 = 当前 7 个稳定 op;50-89 = 新增 op;99 = escape hatch
  oneof op {
    ListGroupsRequest    list_groups    = 10;
    ListStateRequest     list_state     = 11;
    GetStateRequest      get_state      = 12;
    StartRequest         start          = 13;
    StopRequest          stop           = 14;
    RestartRequest       restart        = 15;
    GroupStartRequest    group_start    = 16;  // reserved(尚未实现,P-later)
    GroupStopRequest     group_stop     = 17;  // reserved(尚未实现,P-later)
    GroupRestartRequest  group_restart  = 18;
    // 50-89 留作未来 op:HealthCheckRequest / SnapshotRequest / RollbackRequest / ScaleRequest / ...
    // reserved 50 to 89;
    CustomOpRequest      custom         = 99;  // escape hatch,见 §4.5
  }
  // 注意:永远不要复用已用过的编号。若某 op 废弃,reserved 其编号 + 名字。
}

// ═══════════════════════════════════════════════════════════════
// LifecycleTarget — 统一目标寻址
// ═══════════════════════════════════════════════════════════════
message LifecycleTarget {
  enum Kind {
    KIND_UNSPECIFIED = 0;   // proto3 强制 0 值;server 视为 invalid
    SERVICE          = 1;   // registry.services[].id(当前唯一已实现的种类)
    GROUP            = 2;   // registry.groups[].id
    CONTAINER        = 3;   // reserved for future:直接对 docker container 操作,绕过 service 抽象
    UNIT             = 4;   // reserved for future:直接对 systemd unit 操作
    PROCESS          = 5;   // reserved for future:pid/pgrep/tmux/cmdline_regex
    // 6-15 reserved
  }
  Kind   kind = 1;
  string id   = 2;          // service_id / group_id / container_name / unit_name / ...
}

// ═══════════════════════════════════════════════════════════════
// Op-specific params — 与现有 §2.1 各 handler 期待的 payload 对应
// ═══════════════════════════════════════════════════════════════
message ListGroupsRequest {
  // 现 handler 无参数;保留 message 便于日后加 filter / page 参数
}

message ListStateRequest {
  // 加上 group 过滤(可选,新能力,纯 additive)
  optional string group_id = 1;
}

message GetStateRequest {
  LifecycleTarget target = 1;   // 当前实现只接受 kind=SERVICE
}

message StartRequest {
  LifecycleTarget target = 1;   // kind=SERVICE
  // 未来可选:optional bool force = 2; — 跳过 §5.4 相位矩阵(INVALID_INTENT 不再触发)
  // 用 optional 而不是 bool:区分 "未设置(默认 false)" vs "显式 false"
}

message StopRequest {
  LifecycleTarget target = 1;
  // optional uint32 grace_secs = 2;
}

message RestartRequest {
  LifecycleTarget target = 1;
  // reserved — D-115 cascade 行为是 handler 内置,不作为参数暴露。
  // 未来若需要 --no-cascade 开关:optional bool no_cascade = 2;
}

message GroupStartRequest { LifecycleTarget target = 1; }   // kind=GROUP
message GroupStopRequest  { LifecycleTarget target = 1; }

message GroupRestartRequest {
  LifecycleTarget target = 1;   // kind=GROUP
  // optional uint32 per_member_stop_wait_secs = 2;  // 当前 handler 内置 5s
}

// Escape hatch(§4.5)
message CustomOpRequest {
  string op_name = 1;            // 自由字符串,server 端按注册表路由
  bytes  payload = 2;            // op-specific bytes(通常装 JSON)
}

// ────────────────────────────────────────────────────────────────
message ClientCaps {
  repeated string known_ops           = 1;   // 客户端认识的 op 名字符串
  repeated string known_target_kinds  = 2;
  string          client_version      = 3;
}
```

### 4.3 LifecycleResponse

```proto
message LifecycleResponse {
  string request_id = 1;
  // seq 单调:与现有 DesiredState.seq 对齐,放映后端是否接受了 desired write;
  // 对 read-only op(list/get),seq 可填 0 或省略
  uint64 seq = 2;
  // 与 Envelope.status 对齐, but 增加 PARTIAL for group fan-out(现有 PARTIAL 已在 Status enum)
  Status status = 3;  // OK/ERROR/PENDING/PARTIAL — 与 Envelope.Status 同枚举

  oneof result {
    // op-specific success payload。bytes 容器的内部 schema 见各 op
    // (ListGroupsResult / GetStateResult / GroupRestartResult / ...)
    // 用 bytes 而不是各自 oneof:
    //   - 允许后端独立于信封演进 result schema
    //   - 老的 response parser 仍能拆 envelope,只是不能 interpret bytes
    bytes           ok    = 10;
    LifecycleError  error = 11;
  }
}

enum Status {
  STATUS_UNSPECIFIED = 0;
  OK                 = 1;
  ERROR              = 2;
  PENDING            = 3;   // accepted, actuating
  PARTIAL            = 4;   // group fan-out 部分失败
}

message LifecycleError {
  LifecycleErrorCode code    = 1;
  string             message = 2;   // byte-exact,与 §2.2 表格对齐
  optional string    cause   = 3;   // 链上更深层的 root cause(可选)
}

// 与 §2.2 现有字符串 code 一一对应 — 不改名,不删值
enum LifecycleErrorCode {
  ERROR_CODE_UNSPECIFIED       = 0;   // proto3 占位
  INVALID_INTENT               = 1;   // §5.4 矩阵
  MISSING_FEATURE              = 2;   // 未 expose Lifecycle
  UNKNOWN_SERVICE              = 3;
  UNKNOWN_GROUP                = 4;
  UNKNOWN_OP                   = 5;   // server 收到未知 op(wire format 兼容旧客户端)
  TIMEOUT                      = 6;
  PERMISSION_DENIED            = 7;
  BAD_PAYLOAD                  = 8;
  MISSING_FIELD                = 9;   // 现有 handlers.rs:687
  NO_STATE                     = 10;  // 现有 handlers.rs:384
  EMPTY_GROUP                  = 11;  // 现有 handlers.rs:703
  TOPO_CYCLE                   = 12;  // 现有 handlers.rs:728
  GROUP_MEMBER_STOP_FAILED     = 13;
  GROUP_MEMBER_START_FAILED    = 14;
  UNKNOWN_ACTION               = 15;  // 现有 dispatch 兜底
  BAD_ENVELOPE_BRIDGE          = 16;
  UNSUPPORTED_TARGET_KIND      = 17;  // 未来:kind=PROCESS 但 backend 不支持
  INTERNAL                     = 18;
  // 19-49 reserved for future
}
```

### 4.4 LifecycleTarget 详解

`kind` 枚举的映射规则:

| kind | 当前 target/selector 对应 | 后端处理 |
|---|---|---|
| SERVICE | registry.services[].id | 现有路径,通过 service 找到 provider + selector |
| GROUP | registry.groups[].id | 现有路径(`computed_members_for_group` handlers.rs:462) |
| CONTAINER | selector.container(直名) | 新路径(未来)— backend 直接用 docker provider 而不查 registry service |
| UNIT | selector.unit(直名) | 新路径(未来)— 直接用 systemd provider |
| PROCESS | pid / cmdline / tmux | 新路径(未来) |

**为什么直接寻址(CONTAINER/UNIT)是必要的**:目前所有动作都要先注册一个 service(`registry-robot.yaml:82-263`),但运维偶尔需要"对着一个 fly-by 容器直接 stop"而不想注册。统一 API 必须预留;这次不实现,但 kind=3/4 在 proto 里 reserved 防止未来编号冲突。

### 4.5 CustomOp escape hatch

**用途**:
- 允许 server 端先上线一个新 op(不走 proto 变更),老 client 用 CustomOpRequest 试探;
- 允许研究/调试期一次性 op 注入(test-only)。

**用法约束**:
- Custom op 不得用于生产 path,只在客户端-后端协商允许时使用;
- 收敛路径:CustomOpRequest 使用频率连续 2 周 > 100 次的 op,必须提案升级为正式 oneof 分支;
- `op_name` 命名空间 `x-*`(experimental)保留;不带前缀的 Custom op 在 lint 阶段报警。

### 4.6 Service discovery(dynamic UI 的前提)

`list_groups` + `list_state` 已经在 7 op 之内;前端通过这两个 RPC 动态构建服务/组 selector,**不在前端硬编码任何 service_id**:
1. UI 加载时 `lifecycle.execute { op: list_groups }` → 拿到 group 列表 + `computed_members`;
2. 用户选 group → UI 自动展开 member service 列表;
3. 用户选 service → UI 用该 service 当前 phase(来自 `list_state`)决定哪些按钮可点(对照 §5.4 矩阵客户端预校验);
4. 用户点 Start → `lifecycle.execute { op: start { target: {kind: SERVICE, id: sid} } }`。

这把 UI 从"硬编码 8 服务"变成"对任意 registry 自适配",是统一 API 的直接收益。

### 4.7 Frontend → ArgoGateway:方案 A(Chat 隧道)vs 方案 B(typed LifecycleExecute)

| 维度 | A:复用 Chat | B:新增 LifecycleExecute RPC |
|---|---|---|
| Proto 改动 | 0 | 加 RPC + 2 个 message(LifecycleRequest/Response) |
| ArgoGateway 改动 | 0 | 加 handler:接 RPC → 序列化 protobuf → zenoh publish → 等 result → deserialize 回 RPC response |
| 类型安全 | payload 是 string,前端手写 JSON | 强类型,buf codegen TS 直接用 |
| 调试便利 | Chat history 直接看 payload JSON | 需要专门 RPC 日志 |
| Buf 兼容性 | n/a | 加 RPC + message 是 additive,向前兼容 |
| 演进成本 | 每次 op 加参数,前后端手写一致性 | 改 proto → 重新 codegen,自动一致 |
| **推荐** | **短期(M1)**,先把 backend unified handler 落地跑通 | **中期(M2-M3)**,验证 Chat 隧道稳定后切到 typed |

落地建议:**Phase 1-2(§7)用方案 A,Phase 3+切到方案 B**。Phase 4 删旧 topic 时 typed RPC 已成为主路径。

---

## 5. Versioning & compatibility(用户约束 1,first-class)

### 5.1 Proto field numbering rules(强制)

1. **编号一经发出永不复用**。即便某字段被删除,其编号也必须 `reserved` 而不是允许回收。
2. **删除字段流程**:`optional T foo = N;` → `reserved N; reserved "foo";`(同时 reserved 编号 + JSON 名)。
3. **oneof 内部分支亦然**:`reserved` 分支编号 + 分支名。例如将来 `group_start` 废弃:`reserved 16; reserved "group_start";`。
4. **编号区段规划**(已在 §4.2 注释里写):
   - `1-9`:协议刚性字段
   - `10-49`:当前 7 stable op
   - `50-89`:未来 op
   - `99`:escape hatch
   新业务方块不要插入旧区段,只能占未来区段。
5. **Lint**:在 `ArgoGateway/proto/` 配 `buf.yaml` 启用 `buf breaking` 检测(against main branch),CI 卡关。

### 5.2 Enum unknown semantics

**Proto3 事实**:
- 二进制 wire format:enum 被序列化为 varint,**未知值不会丢失**,接收方按整数存。
- 生成代码层:
  - **Rust(prost)**:`Option<i32>`(proto3 optional)+ `Enum::from_i32()` 返回 `Option`,unknown → `None`;非 optional 直接用 `i32`。
  - **TS(protobuf-es)**:`LifecycleErrorCode` 是 TypeScript `enum`,读到未知值**会保留数字**(`result.code = 42 as LifecycleErrorCode`),并不抛错;但 `LifecycleErrorCode[42]` 是 `undefined`。

**统一定律(写入 DESIGN 作为 contract)**:
- 接收方**不得**因读到未知 enum 值而 panic / throw。
- 接收方必须映射到 fallback:
  - `LifecycleTarget.Kind` unknown → 视为 `KIND_UNSPECIFIED`,handler 报 `UNSUPPORTED_TARGET_KIND`(⊥ — 见 §4.3 enum)而不是 crash。
  - `LifecycleErrorCode` unknown(前端视角)→ UI 显示 `UNKNOWN(${n})`,并把它们一律按 `INTERNAL` 处理(red banner)。
  - oneof `op` unknown branch:wire format 只能解出一种 branch — 旧 client 不识别新 branch 时,prost 给 `op: None`,handler **必须**返回 `UNKNOWN_OP` 错误,而不是默认走某个 branch。

**Rust 端示例(必须遵守)**:
```rust
match req.op {
    Some(Op::Start(p))     => handle_start(p).await,
    Some(Op::Stop(p))      => handle_stop(p).await,
    // ...
    Some(Op::Custom(p))    => handle_custom(p).await,
    None                   => Envelope::error_response(req, "UNKNOWN_OP",
                                 "no recognized op branch set (client may be older than server)"),
}
```

`None` 分支**必须显式存在**,不允许 wildcard `_ => unreachable!()`。

### 5.3 Deprecation window

**背景**:切换期内,旧 7 topic + 旧 `restart_service/start_service/stop_service` Chat action 仍然可服务。要决定何时硬删。

**推荐窗口**:
- **dual-run 期**:Phase 1 上线后到 Phase 3 E2E 全绿 ≥ 2 周,且新 path 流量 ≥ 99%(用 `lifecycle.audit` 日志的 `requester` 字段区分新旧客户端来源)。
- **deprecated 警告期**:再 2 周,backend 在响应 `header` 里塞 `X-Deprecated: true` metadata(或在 audit log 打 warn),提示调用方。
- **hard removal**:Phase 4 一刀切(用户组织内可控,不必走语义化 deprecation 长流程)。

**硬删标准**(全部满足才可删):
- E2E §6 全绿持续 2 周;
- 前端 `demoRobotControl.ts` 的 `restartDemoRobot / startDemoRobot / stopDemoRobot` 已切换到 `runLifecycleExecute`,git log 显示该变更已合入 ≥ 2 周;
- Chat handler 在 ArgoGateway 这侧对 `restart_service|start_service|stop_service` 的调用 rate = 0(用 zenoh 流量或 ArgoGateway access log 度量)。

### 5.4 Schema versioning(`schema_version` 字段:加 vs 不加)

**Pros(加)**:
- 显式表明本消息遵循哪一版 schema,便于 wireshark / 日志 debugging;
- 未来做出"非 additive"修改时(如某字段语义反转),server 可以按 version 走分支;
- CustomOpRequest 内部可以再嵌 `schema_version`,让 escape hatch 也享受显式版本。

**Cons(加)**:
- proto3 的隐含版本(靠 field number / reserved 纪律)实际上已足够。加显式 version 容易给调用方"锁版本就算了"的错觉,放松对 §5.1 纪律的执行;
- 若 version 不匹配,server 该拒还是该容忍?拒——破坏 forward compat;容忍——version 字段就沦为装饰。
- 增加每次请求 4-8 bytes 流量(可忽略,但仍是成本)。

**推荐(明确)**:**短期不加 `schema_version`,但保留字段号 5**。原因:
- 当前只在 additive 演进路径走(加 op / 加 kind / 加 optional 字段),proto3 + reserved 纪律已经够用;
- 若将来真的需要 non-additive 改动(强烈反对,留 §10 open question),把 `optional uint32 schema_version = 5;` 从注释里启用,**不重用已有编号**,保持 wire format 兼容;
- 强制 CI buf breaking 检查作为代码侧替代,比 version 字段更可靠。

### 5.5 Client capability negotiation(`client_caps`:加 vs 不加)

**Pros(加)**:
- Backend 可以裁剪响应:知道 client 不支持某 enum 值就 fallback;
- 允许 server 提示"你的 client 太旧,有些 op 我不会给你跑" → 发送 `UNKNOWN_OP` 而非 silently ignore;
- 多客户端类型(demo web UI / ια CLI / fleet manager)可以走同一条 RPC。

**Cons(加)**:
- 第一版所有 client 的 caps 都是 ( lifecycle.* ) — 没差异化价值;
- caps 自身需要演进(类似 schema_version 的问题,无限递归);
- 增加 server 端复杂度:每个 op handler 都要看 caps 决定行为。

**推荐(明确)**:**v1 保留字段但不实现**(`optional ClientCaps client_caps = 6;` 序列化时总是 unset)。原因:
- proto 必须现在就把字段号占住,防止未来要加 caps 时不得不开新号;
- v1 server **忽略** client_caps(读了就忘),v1 client **不填**;
- 等真有"响应形状需要按 caps 改变"的需求时(目前没看到)再启用,届时作为 **v2 严格 additive 扩展**(老 client 不填 = server 给 v1 默认行为)。

**判断**:这是把 §5.4 的 explicit version vs implicit reserved debate 应用到 caps 上 — 同样的回答,先占位再启用。

### 5.6 Wire format(protobuf binary vs JSON)

| 维度 | protobuf binary | JSON |
|---|---|---|
| 大小 | 紧凑(model replies 节省 ~30-60%) | 大 |
| Schema | 强制;breaking change 由 buf 兜底 | 无强制,容易漂移 |
| 调试 | 需要 protoc --decode / wireshark | 任何 HTTP 工具直接看 |
| ArgoDDS 现有 payload | `serde_json::Value` —— 现状就是 JSON | 沿用 |
| Frontend Connect-RPC | 支持 binary 和 JSON | 支持 |
| Backend Rust | prost + pbjson-types | serde_json(已用) |

**推荐(明确)**:**ArgoGateway ↔ frontend 用 protobuf binary**(Connect-RPC 协议默认);**ArgoDDS zenoh topic 用 JSON**。原因:

1. Frontend ↔ ArgoGateway 已经走 Connect-RPC(robot_control_pb.ts:1),binary 是一等公民,工具链完整;
2. ArgoDDS 侧现存 7 个 topic 的 Envelope 都是 JSON(`envelope.rs` serde_derive,`Header::new_request` 直接 format! RFC3339),维护现状意味着:
   - backend 不需要新增 prost 依赖;
   - `lifecycle.audit` 日志 / zenoh wiretap 工具能直接读;
   - E2E 测试写 assertion 可以用 `jq` / grep,不写 protobuf 解析。
3. 转换代价:ArgoGateway 在方案 B(typed RPC)中需要做一次 protobuf→JSON 转换 LifecycleRequest → Envelope,可接受(单 op 一次转换,<1ms)。

未来若 zenoh topic 流量成为瓶颈(>>1k msg/s),再切 protobuf binary,届时与 schema_version 一并启用。**当前不过度设计**。

### 5.7 Forward-compat 行为矩阵(必须达成的契约)

| 场景 | 老 client | 新 backend | 行为 |
|---|---|---|---|
| C1 | proto v1(只懂 7 op) | v2 加了 `HealthCheck = 50` | client 永远不会发 HealthCheck;backend 不会主动推;✓ 兼容 |
| C2 | v2 加了 HealthCheck | v1 只懂 7 op | client 发 `op = 50`,backend `oneof.op = None` → 响应 `LifecycleError{code: UNKNOWN_OP, message: "no recognized op branch set"}` ✓ |
| C3 | v1 只懂 kind=SERVICE | v2 加了 kind=PROCESS | client 发 kind=1,backend kind=1 → 正常 ✓ |
| C4 | v2 懂 kind=PROCESS | v1 只懂 SERVICE | client 发 kind=5,backend `Kind::from_i32(5) = None` → 响应 `UNSUPPORTED_TARGET_KIND` ✓ |
| C5 | v1 发 StartRequest | v2 给 StartRequest 加了 `optional bool force = 2` | client 不发 force;backend 读到 `force = None` 视为 false,走默认 ✓ |
| C6 | v2 发 StartRequest.force=true | v1 | client 发 field 2 在 wire 上;backend proto v1 不识别 field 2,prost 解析时**忽略未知字段**,按 force=false 处理 ✓ |
| C7 | v1 收 LifecycleError.code=UNKNOWN_OP(5),v1 该枚举只到 4 | — | TS 端把 code=5 保留为数字,UI 显示 "UNKNOWN(5)" 按 INTERNAL 处理 ✓ |

**关键不变量**:任何 additive 变更都不破坏已有路径;任何 non-additive 变更(改字段语义、复用编号)都通过 buf breaking 在 CI 拦截。

---

## 6. End-to-end test plan(用户约束 2,first-class)

### 6.1 E2E 链路

```
[Frontend robot-app-platform/apps/demo]
   │ Connect-RPC over HTTP        (demoRobotControl.ts — 改造后调 runLifecycleExecute)
   ▼
[ArgoGateway server]              ← gRPC server,:50051
   │ 方案 A:chatRPCHandler → build zenoh pub
   │ 方案 B:LifecycleExecute handler → serialize → zenoh pub
   │  topic = /<fleet>/<bot>/watch/lifecycle/execute/submit
   ▼
[ArgoDDS bus (zenoh router)]      ← e.g. argo-zenoh-local.service @ SP000065
   │ broker pub → sub
   ▼
[demo-app-backend]                ← 已 subscribe `watch/lifecycle/execute/submit`
   │ dispatch_action → handle_lifecycle_execute
   │   → 按 payload.op 二次分发到现有 7 个 handler
   ▼
[demo-app-lifecycle Runtime]      ← Desired write + converge_tx
   │
   ▼
[Provider (systemd|docker|http)]  ← PA3 探针 provider = docker exec_process
   │
   │ 响应反向链回:Envelope ok/error → .../result → ArgoGateway → frontend
   ▼
[Frontend] resolves ChatResponse / LifecycleResponse
```

### 6.2 测试矩阵

| 维度 | 值 | 说明 |
|---|---|---|
| Op | 7 stable + 1 hypothetical(HealthCheck = 50) + 1 hypothetical target kind(CONTAINER direct) | 9 个 case |
| Endpoint | (a) frontend → ArgoGateway → ArgoDDS → backend;(b) CLI lifecycle_cli → ArgoDDS → backend | 2 个入口 |
| Registry | 真实 SP000065(`registry-sp000065.yaml`)+ 本地 mock(`registry-mvp.yaml`)| 2 个环境 |
| 总 case 数 | 9 × 2 × 2 = **36**, 但 malicious / no-side-effect 子集只做真实环境(PA3)| 见 §6.3 |

### 6.3 Per-op 测试用例(摘关键)

| Case | Op | Endpoint | Registry | Setup | 期望 status | 期望 error.code | byte-exact 断言 |
|---|---|---|---|---|---|---|---|
| E01 | list_groups | (a) | SP000065 | — | OK | — | `payload.groups[].id` 含 4 元素:`robot-comm, robot-oneshot, robot-stack, robot-stack-members` |
| E02 | list_state | (a) | SP000065 | — | OK | — | `payload.services` 8 元素;`localization-robot-1-docker-exec.phase` ∈ `Running/Stopped` |
| E03 | get_state (valid) | (a) | SP000065 | 目标=`localization-robot-1-docker-exec` | OK | — | `payload.service_id == "localization-robot-1-docker-exec"` |
| E04 | get_state (unknown sid) | (a) | SP000065 | 目标=`no-such-svc` | ERROR | `UNKNOWN_SERVICE` | `unknown service id 'no-such-svc'` (byte-exact) |
| E05 | start (Running→Start INVALID) | (a) | SP000065 | 先确认 probe 已 Running | ERROR | `INVALID_INTENT` | byte-exact 现有 §5.4 message 模板 |
| E06 | start (Stopped→Start OK) | (a) | SP000065 | 目标 stop 后 | OK | — | `payload.accepted == true && payload.seq > 0` |
| E07 | stop (valid) | (a) | SP000065 | 目标 Running | OK | — | `payload.accepted == true` |
| E08 | stop (already Stopped) | (a) | SP000065 | 目标 Stopped | ERROR | `INVALID_INTENT` | byte-exact |
| E09 | restart (valid) | (a) | SP000065 | 目标 Running | OK | — | restart_token 旋转 |
| E10 | restart (no expose) | (a) | SP000065 | 目标=`rustbot-daemon-http`(只 status)| ERROR | `MISSING_FEATURE` | byte-exact |
| E11 | group_restart (topology placeholder = status-only) | (a) | SP000065 | 目标 group=`robot-stack` | ERROR* | `MISSING_FEATURE` | *当前 SP000065 registry 全员 status-only,group verb 必然触发 MISSING_FEATURE — 这是预期拒绝路径 |
| E12 | CLI list_groups | (b) | mock registry-mvp | — | OK | — | schema 同 E01 |
| E13 | CLI start | (b) | mock | 目标=`test-svc` | OK | — | 同 E06 |
| E14 | HealthCheck (hypo, custom) | (a) | SP000065 | server 端用 CustomOpRequest 注册 `x-healthcheck` | OK | — | 客户端通过 `custom: {op_name: "x-healthcheck", payload: b"{...}"}` 调通 |
| E15 | HealthCheck (hypo, oneof=50) 后端未实现 | (a) | SP000065 | server 端 proto 只到 18 | ERROR | `UNKNOWN_OP` | server 收到 oneof.op=None → 拒绝 |
| E16 | target.kind=CONTAINER direct | (a) | SP000065 | kind=3 但 backend 未实现该 kind | ERROR | `UNSUPPORTED_TARGET_KIND` | — |
| E17 | request_id 关联 | (a) | SP000065 | 任意 op | OK | — | `LifecycleResponse.request_id == LifecycleRequest.request_id`;且 backend `Envelope.header.ref_id == req.header.id` |
| E18 | seq 单调 | (a) | SP000065 | 同一 service 连续 3 次 Start/Stop | OK | — | `seq1 < seq2 < seq3`,与 backend `DesiredState.seq` 对齐 |
| E19 | Stop by service 未在 phase 矩阵(StoppED→Stop)| (a) | mock | — | ERROR | `INVALID_INTENT` | message template 与 SP000065 一致 |

### 6.4 测试 fixture

- **请求夹具**: protobuf 用 `pbjson-types` 或 backend `prost` 把 LifecycleRequest 编码;JSON 用现有 Envelope schema;对应 TS 侧用 `@bufbuild/protobuf` codegen。
- **服务夹具**:
  - **专用 e2e service_id** = `localization-robot-1-docker-exec`(PA3 probe),**不动**其它 7 个服务;
  - 该 service 真实调 docker `exec_start = "echo PA3_OK && id && hostname"` — 零副作用,可以反复 Start;
  - **不要**对该 service 调 Stop(已在 registry 注释里说明 stop 永不发,registry-sp000065.yaml:60-69);测试只调 Start/Restart/GetState/ListState/ListGroups;
  - Stop INVALID_INTENT 测试用 `ethers-earning-oneshot`(stop 已被排除)或者 mock registry。
- **Idempotency**: 每 case 生成独立 `request_id = uuid4()`,backend Desired write 用 seq 单调保证;重放同一 request_id 预期 server 端按"已接受,直接返回上次 response"行事 — 但当前实现**不**保证 idempotent(每次 Start 都会 seq++),E2E 里**不**测 idempotent 重放,只测 request_id 关联(§6.5)。
- **Order**: 每个 case 独立;串行执行;对 `localization-robot-1-docker-exec` 的 lifecycle 写操作总次数 ≤ 5 次/测试 run。

### 6.5 测试断言清单

每个 case 必附断言:

```text
1. Transport status   : Connect-RPC 错误码 = OK / RESOURCE_EXHAUSTED / ...
2. Envelope.status    : ∈ { OK, ERROR, PARTIAL }       (JSON path) 或 LifecycleResponse.status  (proto path)
3. Error.code         : ∈ LifecycleErrorCode enum       (若 status=ERROR)
4. Error.message      : byte-exact string 或 regexp    (§2.2 表格)
5. Payload schema     : JSON Schema / prost Debug 形态校验
6. request_id 关联    : resp.request_id == req.request_id
7. seq 单调           : 多 step case 下 seq 递增          (仅 actuate op)
8. audit log          : backend 端 `lifecycle.audit` target emit 一行,含 service_id, op, seq, requester, restart_token
                        — 对应 handlers.rs:166-177 的 audit_line
```

### 6.6 测试环境

- **机器人** = SP000065 (192.168.100.100)
- **访问方式** = 现有 SSH alias `niic_26`(密钥已配置);**禁止**在文档/代码里写密码或 token;
- **运行位置**:E2E 测试 runner 跑在开发者笔记本(wangdang),通过 SSH tunnel 或直连 192.168.100.100 的 ArgoGateway 端口;
- **预条件**:SP000065 上 demo-app-backend 已 deploy 并跑起,argo-zenoh-local 已 Running,docker daemon 可访问 `localization-robot-1` 容器;
- **清理**:测试无需显式清理 — PA3 probe `exec_start` 是只读 echo,不留状态;但 test runner 必须在结束时调一次 `get_state` 确认 phase 不处于 `Failed`(若 Failed → 测试失败并上报告警)。

### 6.7 测试 cadence

- **Pre-merge(PR check)**:仅跑 mock registry 套件(E12, E13, E19)+ 编译 + buf breaking,目标 < 2 min;
- **Post-merge(nightly)**:真机 SP000065 全套 E01-E19,目标 < 10 min;fail 通过 Slack/告警通知;
- **On-demand(发版前)**:人工触发 same as nightly;
- **不建议** pre-merge 跑真机:机器人是稀缺资源,PR 并发会互踩;真机测试只对 main 分支开放。

### 6.8 测试隔离

- **request_id 命名空间**:E2E 用前缀 `e2e-<runid>-<case>-<uuid>` — 避免与生产请求冲突;
- **service_id 命名空间**:E2E 只碰 `localization-robot-1-docker-exec`,其它 8 个 SP000065 service **不**作为 lifecycle 写操作的目标;
- **并发**:E2E runner 内部单线程串行,不并行打同一 service;允许 list/get 类 read-only op 并行;
- **运行 ID**:`runid = <short-sha>-<ts>` 写入每个 request 的 `requested_by`,落到 `lifecycle.audit` 后可用 `journalctl --user -u demo-app-backend | grep e2e` 反查。

### 6.9 Compatibility test(C1 专项)

- **CT-1**:v1 frontend(只懂 7 op)调 v2 backend(加了 HealthCheck)→ 7 个稳定 op 行为完全不变;
- **CT-2**:v2 frontend(发 HealthCheck)调 v1 backend → 收到 `LifecycleErrorCode.UNKNOWN_OP`,UI 按 INTERNAL fallback 显示红色 banner;
- **CT-3**:v2 frontend 发 `target.kind=CONTAINER direct` 调 v1 backend → `UNSUPPORTED_TARGET_KIND` byte-exact;
- **CT-4**:Start v2 字段 force=true 调 v1 backend → backend 忽略 force 字段,按默认 false 执行;frontend 收到 OK;
- **CT-5**:partial upgrade = 部分 backend 已升级(2/3 fleet)+ 前端 v2。预期:已升级的 backend OK,未升级的 UNKNOWN_OP,前端聚合报告"partial support"并能 fallback。

CTS 通过方式:版本 mock(在 test binary 里编译两份 schema)+ 真机 SP000065(主流 scenario)。

---

## 7. Migration path(4 phases,双轨)

### Phase 1 — additive backend
- demo-app-lifecycle 加 `ACTION_LIFECYCLE_EXECUTE = "lifecycle.execute"`;
- 加 `handle_lifecycle_execute(rt, req)`:解析 `payload.op` → 路由到现有 7 个 handler;
- demo-app-backend `dispatch_action` 加一条 arm;
- **不动**旧 7 topic;新旧并存。
- **完成判据**:`cargo build -p demo-app-lifecycle`;能用手工 zenoh pub 把 `lifecycle.execute` Envelope 送进去并收到正确响应。

### Phase 2 — frontend + ArgoGateway
- 短期方案 A:`demoRobotControl.ts` 加 `runLifecycleExecute(op, target, params)`,内部继续走 Chat RPC,`command = "watch/lifecycle/execute/submit"`;
- 在 demo 页把 `restartDemoRobot / startDemoRobot / stopDemoRobot` 切到新函数;
- 中期方案 B:ArgoGateway 加 `FrontendRobotControlService.LifecycleExecute` RPC + proto message;frontend 切到 typed RPC;**完成判据**:Typed RPC 连续 7 天无 error,Chat 隧道路径流量降到 < 1%(audit log 统计)。

### Phase 3 — verify on SP000065(E2E,见 §6)
- 跑 §6 nightly 全套;
- **完成判据**:E01-E11 + E17 + E18 = 13/13 PASS;byte-exact INVALID_INTENT/MISSING_FEATURE 与现网 V5 §3 完全一致。

### Phase 4 — deprecate
- 满足 §5.3 硬删标准后:
  - demo-app-backend 删 `ACTION_LIFECYCLE_START ... GROUP_RESTART` 7 个 match arm + 7 个 topic 订阅;
  - 删 lifecycle handler `handle_lifecycle_start/stop/...`(它们已由统一 dispatcher 复用其内部逻辑,**外壳函数**可删,内部 `lifecycle_control` 私有函数保留);
  - Chat action `restart_service/start_service/stop_service` 的 handler(若仍存在;按当前 backend handlers.rs:374-460 已 retire,只需确认 ArgoGateway 这边 Chat 路由不再 special-case 它们);
  - 文档刷新:arch doc §5 / SPEC §6 里把 7 topic 改成 1 topic。

---

## 8. Frontend integration

**新 API surface**(`demoRobotControl.ts` 增加,与现有 `runChatCommand` 平行):

```typescript
export type LifecycleOp =
  | { kind: "listGroups" }
  | { kind: "listState"; groupId?: string }
  | { kind: "getState"; target: LifecycleTargetRef }
  | { kind: "start"; target: LifecycleTargetRef }
  | { kind: "stop"; target: LifecycleTargetRef }
  | { kind: "restart"; target: LifecycleTargetRef }
  | { kind: "groupRestart"; target: LifecycleTargetRef }
  | { kind: "custom"; opName: string; payload: unknown };

export type LifecycleTargetRef = { kind: "service"|"group"|"container"|"unit"|"process"; id: string };

export async function runLifecycleExecute(
  session: DemoRobotControlSession,
  op: LifecycleOp,
  timeoutMs = 10_000,
): Promise<LifecycleResultShape>;
```

**内部实现**:方案 A 期把 `op` 序列化成 JSON;方案 B 期序列化成 protobuf LifecycleRequest。Surface 不变。

**UI 影响**:
- 把现有 demo 页 start/stop/restart 按钮底层都切到 `runLifecycleExecute`;
- 新增"服务选择器"组件,数据源 = `runLifecycleExecute({kind:"listGroups"}) + ({kind:"listState"})`;
- 按钮 enable/disable 由 §5.4 矩阵在 client 侧预校验(同样规则);backend 仍是 authoritative。

---

## 9. Risks & tradeoffs

| 风险 | 描述 | 缓解 |
|---|---|---|
| oneof vs string op | 用 oneof 需要每加一个 op 改 proto;用 `string op + bytes payload` 完全不动 proto 但失去类型约束 | **选 oneof + escape hatch**:稳定 op 走 oneof 享受类型;不稳定的走 CustomOpRequest §4.5 |
| Payload bytes vs 强类型 | ok: bytes 给后端演进空间,但 frontend 不再是 self-typed | 每个 op 在 proto 里也定义对应 `*Result` message;`bytes` 就是该 message 的 serialized。Frontend 知道 op → 知道用哪个 message decode |
| Escape hatch 滥用 | 永远走 custom 不收敛 | §4.5 的 lint rule:`x-*` 命名 + 生产路径禁用 + 频次监控 |
| Back-compat 成本 | 双跑期 backend 要同时维护 7 topic + 1 unified | §5.3 硬指标(流量 < 1% / 2 周)到期即切 |
| Proto 版本演进 | buf breaking 需要 CI 强制 | Phase 1 PR 同时加 `buf.yaml` + GitHub Action;不依赖人 |
| Error enum exhaustive | switch 没处理全 | 后端 `match` 必须包含 `None => UNKNOWN_OP` 兜底;前端 ts 用 `switch + default: return INTERNAL` 兜底 |
| E2E 复杂度 | 36 case 不轻 | Pre-merge 只跑 mock 子集,真机 nightly;E16/E17/E18 之类的 contract 断言做成 reusable matcher |
| Dual-write 成本 | Phase 1-2 期新旧都要写监控/告警 | `lifecycle.audit` 已统一两个 handler namespace,无重复 |
| Demo 页 UI 改动 | 现有调用都要切 | runLifecycleExecute 设计为 drop-in replacement,不改 UI 结构,只改 handler 内部 |
| 删 Chat 时机 | Chat 是其它 action(logs/robot_status)的隧道 | 只删 lifecycle 走 Chat 的用法,Chat RPC 本身保留给其它场景 |

---

## 10. Open questions(给 orchestrator / 用户决策)

1. **Proto 文件位置**:`gateway.v1` 包下新建 `lifecycle.proto`,还是塞现有 `robot_control.proto`?倾向**新文件**,便于按业务域拆分。owned by ArgoGateway repo 还是 shared proto repo?
2. **`schema_version` 字段是否首版就启用**(§5.4 推荐"占位不启用",如果用户倾向"显式 version"那可以改)?
3. **`client_caps` 是否 v1 就启用**(§5.5 推荐"占位不启用")?
4. **Stream vs unary**:`LifecycleExecute` 是 unary(请求-响应);group_restart 这类长时间 op 是否需要 stream 进度?(当前后端已经是 fire-and-forget,进度通过 get_state 轮询 — 推荐保持 unary,不引入 stream)。
5. **其它 action namespace 是否也统一**:`robot.status / robot.operational / logs.collect` 等(demo-app-backend handlers.rs:447-453)是否也走 `unified.execute`?推荐本期**不扩**,只做 lifecycle;但 schema 设计上把 `LifecycleRequest.request_id` 等字段名起得够通用,未来要抽象出 `UnifiedRequest` base 时容易。
6. **`x-*` escape hatch 的 lint 工具**:在哪里跑 lint?pre-commit hook?buf plugin?
7. **§5.4 Completed 相位语义**:P4/V3-C1 已把 `Restart` 对 `Completed` 开放,是否要同步开放 `Stop` from `Completed`?(目前不开放 — 矩阵:Stop 不允许 Completed;保留现状。)
8. **Phase 4 硬删时,ArgoGateway 是否要给旧 topic 订阅者 1 个 grace 期 RPC error `MIGRATED` 而非直接退订阅**(短期 404 vs 显式 migrated error)— 影响调用方体验。

---

## 11. Files in write-set

- `Gawain/workflow/handoffs/lifecycle-unified-api-design/DESIGN.md`(NEW,本文件,~ 550 行)

0 src 修改。0 git 操作。0 host 改动。

---

## 附录 A — ESCALATE(无)

本次设计所需文件全部可访问;无 ESCALATE 项。

## 附录 B — 关键源码引用一览

| 引用点 | 文件:行 |
|---|---|
| 7 op Action 常量 | `ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/handlers.rs:33-41` |
| Phase 合法性矩阵(§5.4)| 同上 `:53-69` |
| preflight + INVALID_INTENT 生成 | 同上 `:73-94` |
| D-115 restart 级联 | 同上 `:280-345` |
| group_restart 实现 + MISSING_FEATURE | 同上 `:683-802` |
| Envelope schema | `demo-app-lifecycle/src/envelope.rs:9-105` |
| Topic extractor + reply infer | `demo-app-lifecycle/src/topic.rs:12-44` |
| Backend dispatch 7 arm | `demo-app-backend/src/handlers.rs:390-426` |
| Retired_actions(legacy Chats)| `demo-app-backend/src/handlers.rs:13-23` |
| SP000065 registry(P5 dogfood)| `demo-app-lifecycle/examples/registry-sp000065.yaml:1-136` |
| 未来拓扑 registry(18 svc) | `demo-app-lifecycle/examples/registry-robot.yaml:1-344` |
| FrontendRobotControlService 11 RPC | `frontend/robot-app-platform/packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts:1534-1658` |
| Chat RPC | 同上 `:1639-1643` |
| runChatCommand(generic 隧道) | `frontend/robot-app-platform/packages/gateway-client/src/lib/demoRobotControl.ts:239-258` |
| 现有 lifecycle DemoRobot 调用 | 同上 `:356-378` |
| ArgoDDS 主题约定 | `ai-stack/docs/argo/argo-data-bus-ai-reference.md`(仅引用,不粘贴)|
