# PROMPT-W8 — skyline studio 同类问题审查 + log 状态对照 (kimi-k3, read-only)

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's three questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: code_review
  permission_mode: bypassPermissions   # read-only audit — write-set EMPTY
```

---

You are **W8** — a one-shot, **read-only audit** worker. demo app 上的 3 个 bug 已通过 W2 找到 + W4/W5 修复（详见 W2/W4/W5 报告）。用户现在要求：把 demo 的 fix 经验套到 skyline studio 上，看 skyline 是否会遇到同类问题；同时把 log 状态也纳入审查。

**Write-set is EMPTY.** Read-only audit，不修改任何文件。

## CRITICAL: NO PARTIAL RETURNS

完成全部检查后按输出契约报告。3-min no-response on a file = ESCALATE + move on。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W2.log` — W2 报告（demo 根因 `client_dir()` line 66-74 用 `HOME` env var）
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log` — W3 报告（demo 0 tracing + 5 处 `String(error)` bug + AppError 无 cause）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W4.log` — W4 报告（demo P0 实施：`tls_log` + `AppError.cause` + `extractInvokeErrorMessage`）
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W5.log` — W5 报告（demo `client_dir()` USERPROFILE 兜底）
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Background — demo 的 3 个已修 bug

| Bug | demo 位置 | demo 修复 |
|---|---|---|
| `client_dir()` 用 `HOME` env var，Windows 缺失回退 `.` 找不到 cert | `argo_tls.rs:66-74` | W5: 加 `USERPROFILE` 兜底 + `tls_log` 记录解析路径 |
| 5 处 `String(error)` 把 Tauri invoke 拒绝的 plain object `{name,message}` 变成 `"[object Object]"` | `transport.ts:302/362`、`robot-sdk.ts:136`、`manage-robot.tsx:267/391/523/652` | W4: 加 `extractInvokeErrorMessage` helper + 5 处修复 |
| `argo_tls.rs` 0 tracing + `AppError::RequestFailed` 无 cause 字段 | `argo_tls.rs` 全文 + `error.rs` | W4: `tls_log` 写 `~/.argo-tls/argo-tls-debug.log` + 10+ 决策点埋点 + `AppError` 加 `cause: Option<String>` + `request_failed_with_cause` helper |

## Environment

- 全部本地 read，无 SSH
- 3-min no-response = ESCALATE + move on

## Checks

### A. skyline `argo_tls.rs` — `client_dir()` 是否有 HOME bug

文件：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs` (574 行)

读全文。重点查：
1. 是否有 `pub fn client_dir()` 或同名函数？grep `client_dir`、`HOME`、`USERPROFILE`、`CLIENT_DIR_ENV`
2. 如果有，quote 它的函数体，对照 demo W5 修复前的 baseline（`std::env::var("HOME").unwrap_or_else(|_| ".".to_string())`）和 W5 修复后（`USERPROFILE` 优先 → `HOME` 兜底）
3. 是否有 `tls_log` 函数（W4 在 demo 加的）？grep `tls_log`、`argo-tls-debug.log`、`writeln!` 配合 `OpenOptions`
4. `apply_mtls` / `build_http_client` / `client_ca_cert_pem` / `gateway_mtls_proxy` / `forward_mtls_stream` / `parse_allowed_gateway_url` 等关键决策点是否有 tracing？逐个列出
5. `argo_tls.rs` 中是否有 `AppError::request_failed(format!("...{e}"))` 出口？是 plain `request_failed` 还是 `request_failed_with_cause`？

### B. skyline 是否有独立 `error.rs`

文件：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/error.rs`

读全文（如果存在）。重点查：
1. `AppError` enum 是否有 `RequestFailed` variant
2. `RequestFailed` 是否有 `cause: Option<String>` 字段（demo W4 加的）
3. 是否有 `request_failed_with_cause` helper
4. 是否用 `#[serde(tag = "name")]` 表示为 plain object

如果 skyline **没有** `error.rs`（看目录列表似乎没有）— 找 skyline 的 `AppError` 定义在哪（grep -r "enum AppError" 全 src-tauri）。可能在 `lib.rs` 里。quote 它的定义。

### C. skyline `Cargo.toml`

文件：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/Cargo.toml`

读全文。重点查：
1. `rustls` 依赖版本 + features（对比 demo: `rustls = { version = "0.23", default-features = false, features = ["ring"] }`）
2. `reqwest` 依赖（对比 demo: `reqwest = { version = "0.11", default-features = false, features = ["json", "multipart", "rustls-tls", "stream"] }`）
3. `tauri-app-log` 依赖是否存在（demo 有 `tauri-app-log = { path = "../../../crates/tauri-app-log" }`）
4. `tracing` / `tracing-subscriber` / `log` / `env_logger` 是否存在
5. `[profile.release]` 是否有 `windows_subsystem = "windows"` 注释配置（影响 release 下 stderr 是否丢）
6. `main.rs` 是否有 `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]`（读 `apps/skyline/src-tauri/src/main.rs`）

### D. skyline `lib.rs` — 是否有 Tauri 命令注册 TLS log + `CryptoProvider` install

文件：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs` (38992 bytes / 估计 1000+ 行)

只读关键片段：
1. grep `rustls::crypto` — 是否有 `default_provider().install_default()` 调用
2. grep `taskflow_debug_log` / `demo_tts_debug_log` / `game_debug_log` / `tls_debug_log` — skyline 有没有类似的 Tauri 命令写 app_data_log
3. grep `eprintln!` / `println!` / `tracing::` — skyline 现有 log 模式
4. grep `DOUBAO_DEBUG` / `RUST_LOG` — env var 控制
5. grep `register_app_data_log` / `append_app_data_log_line` — 是否用 `tauri-app-log` crate

### E. skyline `runtime_log/` 目录

`ls -la /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/runtime_log/` (从 src-tauri/src 列表看到)

skyline 有一个 `runtime_log` 子目录 — 看 skyline 是否有比 demo 更完善的 runtime log 基建。读目录里的所有 .rs 文件（应该不多），quote 关键 API。

特别看：
1. 是否有 `RuntimeLogger` 之类的结构
2. 是否有写文件 + 滚动 + 大小限制的实现
3. 是否能复用到 TLS 调试 log（替代 demo 的 `tls_log` 简陋实现）

### F. skyline JS 侧错误传播链 — `String(error)` bug 检查

skyline 是 React 19 应用，结构不同于 demo。先看：
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/services/` — 有没有 robot-sdk 类似物
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/features/` — 业务模块
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/routes/` — 路由（含 manage-robot 类似页面？）
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/queries/` — TanStack Query

grep 全 skyline/src 下的 `String(error)` / `String(err)`、`error instanceof Error`、`error?.message`、`invoke<MtlsProxyResponse>`：

```bash
grep -rn "String(error)\|String(err)\|error instanceof Error\|invoke<MtlsProxyResponse>" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/
```

也 grep `gateway_mtls_proxy`、`gateway_mtls_proxy_stream` 看 skyline JS 是否调用同样的 Tauri 命令（意味着会走同样的错误传播路径）。

也 grep `extractInvokeErrorMessage` — 看 skyline 是否已经有 W4 helper（可能从 packages/gateway-client 共享？）

特别注意：`packages/gateway-client/` 是否被 skyline 复用？如果是，那 W4 在 `transport.ts` 加的 `extractInvokeErrorMessage` helper skyline 也享受到了。grep skyline 源码看是否 import `@gateway-client` 或类似包名。

### G. skyline 是否有 `TlsFailDialog` 类似组件

grep skyline src 下的 `TlsFailDialog` / `tls.*fail` / `TLS.*handshake`：

```bash
grep -rni "TlsFailDialog\|tls.*fail\|TLS.*handshake" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/
```

如果有类似 dialog，quote 它的 reason 字段渲染处。

### H. W4 同步检查 — `packages/gateway-client/` 是否被 skyline 复用

如果 skyline 也用 `packages/gateway-client/`，那 W4 在 `transport.ts` 加的 helper skyline 已经享受到了，只剩 skyline 独有的 catch 块需要修。

`grep -rn "gateway-client" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/`

`grep -l "from.*gateway-client" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/ -r`

### I. skyline 整体 log 状态盘点

汇总 skyline 现有 log 机制：
1. `tauri-app-log` crate 是否被 skyline 用（grep `tauri_app_log`、`append_app_data_log`）
2. `runtime_log/` 子模块做什么
3. `eprintln!` / `println!` 在 skyline src-tauri 中的使用频率（`grep -c eprintln apps/skyline/src-tauri/src/*.rs`）
4. `tracing` crate 是否被 skyline 使用
5. skyline 的 release 构建日志可见性（`windows_subsystem` 配置 + 是否有 console 子系统切换）

## Output contract (Chinese, <800 words)

### 1. skyline `argo_tls.rs` `client_dir()` 状态

- 函数位置 + 行号 + 完整函数体 quote
- 是否有 HOME bug（`std::env::var("HOME")` 无 USERPROFILE 兜底）
- 是否有 `tls_log` 或等价 tracing
- 决策点埋点清单（与 demo W4 §2 对照）

### 2. skyline `AppError` 状态

- 定义位置（error.rs 或 lib.rs）
- 完整 enum 定义 quote
- 是否有 `cause` 字段
- 是否有 `request_failed_with_cause` helper

### 3. skyline `Cargo.toml` 关键依赖对照

| 依赖 | demo | skyline |
|---|---|---|
| rustls | 0.23 ring | ? |
| reqwest | 0.11 rustls-tls | ? |
| tauri-app-log | yes | ? |
| tracing | NO | ? |

### 4. skyline `lib.rs` 关键 TLS 配置

- CryptoProvider install 位置 + 行号
- 现有 TLS 相关 Tauri 命令
- 现有 log 模式（eprintln / tracing / app_data_log）

### 5. skyline `runtime_log/` 模块概览

- 文件清单 + 关键 API
- 是否可复用做 TLS 调试 log（比 demo 的 `tls_log` 简陋实现更好）

### 6. skyline JS 侧 `String(error)` bug 检查

- 5 处等价位置的 skyline 对应代码（如有）
- skyline 是否复用 `packages/gateway-client` 的 `extractInvokeErrorMessage` helper
- skyline 独有的 catch 块位置

### 7. skyline 是否有 `TlsFailDialog` 等价物

- UI 是否有 TLS 失败弹窗
- reason 字段渲染处是否也有 `[object Object]` 风险

### 8. skyline 整体 log 状态盘点

- 既有 log 基建清单
- 与 demo 的差异
- 哪些 demo 修复可以**直接复用**（packages/gateway-client 共享），哪些需要**单独应用到 skyline**

### 9. 推荐方案矩阵（供 orchestrator 决定是否派 W9）

- **P0**：skyline `client_dir()` 加 USERPROFILE 兜底（复制 W5 修复）
- **P0**：skyline `AppError` 加 cause 字段（复制 W4 修复）
- **P0**：skyline 独有 catch 块的 `String(error)` bug 修复
- **P1**：skyline 加 `tls_log` 或复用 `runtime_log` 模块
- **P2**：其他

每项给出**具体文件 + 行号 + diff 片段**建议。

### 10. ESCALATEs

所有未找到的文件、判断分歧、不明确信号。

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write any file (write-set EMPTY)
- Don't SSH to any host
- Don't run git operations beyond HEAD-guard
- Don't run cargo / bun / just / npm
- Don't dispatch sub-agents
- Don't ask the user any questions — judgment calls → ESCALATE
