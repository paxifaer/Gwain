# SPEC-4 — 实施 W3 P0 方案：客户端 TLS log + JS String(error) bug 修复

## Goal

W3 已完成代码审查（报告 `handoffs/windev2-demoapp-log-check/out-W3.log`），确认：
1. 客户端 `argo_tls.rs` (1179 行) **0 条 tracing/eprintln/app_data_log** — 所有 TLS 决策点静默
2. 客户端 JS 侧 5 处 `String(error)` bug，把 Tauri invoke 拒绝返回的 `{name, message}` plain object 变成 `"[object Object]"`
3. `AppError::RequestFailed` 无 cause 字段，错误链被 `format!("...{e}")` 拍平丢失
4. 服务端有 tracing 基建但 TLS accept 路径 0 条 log（W4 不动服务端，留 P1）

用户已确认 "加快进度,尽量少测试,我这边来测试" — W4 只改代码，不跑 cargo build/test，用户自己 `just dev` 测试。

W4 是 **代码修改** worker（非 read-only）。Write-set 严格限定在下列文件。

## P0 实施方案

### P0.1 客户端 Rust：`argo_tls.rs` 加 TLS 决策点 log

**方案**：在 `argo_tls.rs` 顶部加一个 `tls_log(msg: impl AsRef<str>)` 私有函数，直接写文件到 `~/.argo-tls/argo-tls-debug.log`（与 cert 同目录），不依赖 `AppHandle`、不加新 crate 依赖。日志格式：`[ISO8601-ish] <event> key=value…`。

**实现细节**：
- 路径解析：复用 `argo_tls.rs` 现有 `~/.argo-tls/` 路径逻辑（看 `client_ca_cert_pem` line 115-123 怎么取的 home dir）。Windows 走 `USERPROFILE`，Linux/macOS 走 `HOME`。如果代码已有 `home_dir()` 工具函数，复用。
- 时间戳：用 `std::time::SystemTime::now().duration_since(UNIX_EPOCH).as_millis()` 输出毫秒数即可（不加 chrono）。格式：`[ms:1700000000123]` 或 `[argo_tls t=...]`。
- 文件 IO：`std::fs::OpenOptions::new().create(true).append(true).open(path)`，每行一个 `writeln!`，错误吞掉（不能让日志本身 panic 业务）。
- 大小限制：用 `append_app_data_log_line_with_limit` 模式但**不需要 AppHandle**——直接读文件大小，超过 5MB 截掉前半（或用 `std::fs::read_to_string` + tail 1MB + write）。或者**简化**：不加限制，让用户自己删（先简化，P2 再补）。
- 触发条件：**始终写日志**（无 env var gate），因为日志文件在用户 home 下，用户可以随时删；TLS 失败时用户主动去查；不写日志就没意义。

**决策点覆盖**（每个点至少一条 `tls_log` 调用，事件名清晰）：
- `root_cert_resource_path` (~line 20-29) — `tls_log("root_cert_resource_path candidates tried")` + 命中分支
- `load_client_identity` (~line 80-97) — PEM 解析失败、certs 为空、key 解析失败的每个分支
- `client_identity_pem` (~line 102-108) — `read` 失败
- `client_ca_cert_pem` (~line 115-123) — 哪条路径 hit、哪条 miss、字节数、SHA1 前 8 位（用 `Get-FileHash` 等价的 std impl 或直接打印字节数）
- `apply_mtls` (~line 142-168) — 4 个 AppError 出口前，打 `apply_mtls step=<step> err=<e?>`，err 用 `{:?}` Debug
- `build_http_client` (~line 180-185) — `builder.build()` 失败前打 log
- `parse_allowed_gateway_url` (~line 278-291) — 3 个 reject 分支前打 log + 解析成功后打 URL
- `gateway_mtls_proxy` (~line 300-346) — line 304 `build_http_client` 入口、line 317-320 reqwest send 失败前打 log
- `forward_mtls_stream` (~line 383-459) — line 391、line 407 send 失败前打 log
- `gateway_mtls_proxy_stream` (~line 472-495) — line 477 reject 前、line 484 spawn 失败前打 log

**约束**：
- 不改函数签名（不加 AppHandle 参数）—— `tls_log` 用全局文件路径，从 `~/.argo-tls/` 取，所有函数都能调
- 不加新 crate 依赖（不用 `tracing`、`chrono`、`dirs`）
- log 调用失败不能 panic 业务（用 `let _ = ...` 吞）
- 日志文件路径 `~/.argo-tls/argo-tls-debug.log` 与 cert 同目录

### P0.2 客户端 Rust：`error.rs` 加 `cause` 字段

`AppError::RequestFailed` 现在是 `RequestFailed { message: String }`。改成：
```rust
RequestFailed {
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    cause: Option<String>,
}
```

所有 `AppError::request_failed(format!("...{e}"))` 调用点，把 underlying error 的 `{:?}` Debug 字符串塞到 `cause`：
```rust
AppError::request_failed_with_cause(format!("TLS handshake failed"), format!("{:?}", e))
```
或直接构造 `AppError::RequestFailed { message: format!("..."), cause: Some(format!("{:?}", e)) }`。

如果 `AppError` 有 `request_failed(s: impl Into<String>)` 这样的 helper，加一个 `request_failed_with_cause(s, cause)` 同伴。所有 `argo_tls.rs` 的 4 个 AppError 出口都用带 cause 的版本。

### P0.3 客户端 JS：`extractInvokeErrorMessage` helper + 5 处 bug 修复

**新 helper**（加到 `packages/gateway-client/src/lib/transport.ts` 顶部 export 出去，或新文件 `packages/gateway-client/src/lib/extract-error.ts`）：

```typescript
export function extractInvokeErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object") {
    const obj = error as { message?: unknown; name?: unknown };
    if (typeof obj.message === "string" && obj.message.length > 0) return obj.message;
    if (typeof obj.name === "string" && obj.name.length > 0) return `${obj.name}: ${JSON.stringify(error)}`;
    return JSON.stringify(error);
  }
  return String(error);
}
```

**5 处 bug 修复**（全部改用 helper）：

1. `transport.ts` line 302 — `err instanceof Error ? err : new Error(String(err))` 改为 `new Error(extractInvokeErrorMessage(err))`
2. `transport.ts` line 362 — `invoke<MtlsProxyResponse>("gateway_mtls_proxy", ...)` 加 try/catch 包裹，catch 中用 helper 提取 message 后 throw new Error
3. `robot-sdk.ts` line 136 — `error instanceof Error ? error.message : String(error)` 改为 `extractInvokeErrorMessage(error)`
4. `manage-robot.tsx` line 267 / 391 / 523 / 652 — 同上
   - 特别注意 523 行：`setTlsFailDialog({ open: true, reason: message })` — 把 `[object Object]` 塞进 dialog 的 reason，用户看到的就是 `[object Object]`。修了 helper 这行就对了。

**注意**：
- 不要引入新 npm 依赖
- 不要改其他无关 catch 块
- biome 格式化保持一致（用现有缩进风格）

### P0.4 不动的部分

- **不动** `lib.rs`（不需要新 `tls_debug_log` Tauri 命令，因为 `tls_log` 直接写文件）
- **不动** `Cargo.toml`（不加新 crate 依赖）
- **不动** 服务端代码（W3 的 P1 服务端 tracing 留给后续）
- **不动** `tauri-app-log` crate
- **不动** 测试文件（除非现有测试因 `cause` 字段 break）

## Inputs

- 客户端代码根目录：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/`
- W3 报告：`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log`
- 文件清单（write-set）：
  - `apps/demo/src-tauri/src/argo_tls.rs` (1179 行)
  - `apps/demo/src-tauri/src/error.rs` (103 行)
  - `packages/gateway-client/src/lib/transport.ts`
  - `apps/demo/src/services/robot-sdk.ts`
  - `apps/demo/src/routes/manage-robot.tsx`
- 可选新文件：`packages/gateway-client/src/lib/extract-error.ts`（若选择独立文件而非内嵌 transport.ts）

## Constraints

- **Write-set 严格限定**。其他文件不动。如需新增 helper 文件，必须在上述列表内或 ESCALATE。
- **不跑 cargo build/test/clippy**。用户会自己 `just dev` 测。
- **可跑一次 `cargo check -p SudoRobot`** 验证编译（10-30s 增量），如果超 2 min 则 ESCALATE 跳过。
- **不跑 just dev**。
- **不跑 npm/bun 测试**。
- **不修改 Cargo.toml**（不加新 crate 依赖）。
- **不动服务端代码**。
- **不 git push、不 git commit**（如果用户问起再说）。
- 3-min no-response on a file = ESCALATE + move on。
- 不臆造：找不到的函数明说 NOT FOUND。
- 遵循 biome 格式化风格（TS）和 cargo fmt 风格（Rust），但不主动跑 fmt 命令。

## Output contract (Chinese, <800 words)

### 1. 改动文件清单

逐文件列出：
- 文件路径
- 改动行号范围 + 改动摘要（一两句话）
- 关键 diff 片段（不是完整 diff，是关键 5-10 行片段）

### 2. `argo_tls.rs` log 覆盖

- `tls_log` 函数实现位置 + 行号 + 完整函数体
- 决策点 log 调用清单：函数名 + 行号 + log 事件名 + 期望输出格式

### 3. `error.rs` cause 字段

- 改动后的 `AppError` enum 定义（完整 quote）
- `argo_tls.rs` 4 个 AppError 出口的改动（用新 `request_failed_with_cause` 还是直接构造）

### 4. JS helper + 5 处 bug 修复

- `extractInvokeErrorMessage` 函数位置 + 完整体
- 5 处 bug 修复的 diff（每处 3-5 行 before/after）

### 5. `cargo check` 结果（若跑）

- 命令 + 用时
- 错误（如有）+ ESCALATE

### 6. ESCALATEs

所有未做的检查、判断分歧、跳过的步骤。

End with: `Elapsed: <m>min<s>s`.

## Verification

W4 报告交付后，用户会自己：
1. `just dev-demo` 启动 Tauri
2. 在 windev2 上点击 TLS 连接 SP000065
3. 查 `~/.argo-tls/argo-tls-debug.log` 看客户端 log
4. 查 UI 是否显示真实错误（不是 `[object Object]`）

W4 不需要自测——用户测。
