# PROMPT-W10 — skyline studio P0 修复（复制 W4 tls_log + W5 USERPROFILE 兜底） (kimi-k3, code edit)

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
  reason: code_edit
  permission_mode: bypassPermissions
```

---

You are **W10** — a one-shot, **code-edit** worker. demo app 的 W4+W5 修复已验证 TLS 通了。W8 审查发现 skyline studio 有相同的 `client_dir()` HOME bug（`apps/skyline/src-tauri/src/argo_tls.rs:65`）+ 全文 0 tracing。用户要立刻能用 skyline，所以现在复制 demo 的 P0 修复到 skyline。

**与 demo 的差异**（W8 §6-7 已确认）：
- skyline **没有** `AppError` enum，用 `Result<_, String>` → **不需要** cause 字段修复
- skyline JS 侧 `String(error)` **不是 bug**（Rust 返回 String，String(error) no-op 正确）+ skyline 复用 `packages/gateway-client` 已自动获得 W4 helper → **不需要** JS 修复
- 所以 W10 只动 skyline `argo_tls.rs` **一个文件**

## CRITICAL: NO PARTIAL RETURNS

W10 任务小（1 文件，加 `tls_log` 函数 + 改 `client_dir()` + 决策点埋点）。直接做完并按输出契约报告，不要 status update。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W4.log` — W4 报告（demo `tls_log` 完整函数体 §2 + 决策点埋点清单）
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W5.log` — W5 报告（`client_dir()` USERPROFILE 修复 diff）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W8.log` — W8 报告（skyline 现状 + §1 函数行号清单 + §9 推荐矩阵）
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- 单文件本地编辑
- 可跑 `cargo check -p SudoRobot-skyline` 或对应 package 名（查 `apps/skyline/src-tauri/Cargo.toml` 第 1-3 行的 `[package] name=`）
- 不跑 cargo build/test/clippy
- 3-min no-response = ESCALATE

## Write-set (strictly bounded)

**只修这 1 个文件**：
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs`

**不动其他任何文件**（包括 lib.rs、Cargo.toml、JS 文件、`packages/gateway-client/`）。

## Steps

### Step 1: Read demo `argo_tls.rs` 的 W4 `tls_log` 实现

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs` line 16-46（W4 加的 `tls_log` 函数），quote 它的完整函数体。这是要复制到 skyline 的模板。

### Step 2: Read skyline `argo_tls.rs` 当前状态

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs` 全文（574 行）。

按 W8 §1 的决策点清单找位置：
- `client_dir` line 59-67（HOME bug）
- `root_cert_resource_path` line 13-22
- `load_client_identity` line 73-90
- `client_identity_pem` line 93-99
- `client_ca_cert_pem` line 106-114
- `apply_mtls` line 132-158
- `build_http_client` line 165-173
- `parse_allowed_gateway_url` line 266-279
- `gateway_mtls_proxy` line 289-333

（行号以 W8 报告为准，但请按实际代码定位，skyline 可能略有偏移）

### Step 3: 加 `tls_log` 函数

在 skyline `argo_tls.rs` 顶部（`use` 语句后，第一个函数定义前）加 `tls_log` 函数，**完全照抄** demo W4 版本：

```rust
fn tls_log(msg: impl AsRef<str>) {
    use std::io::Write;
    use std::time::{SystemTime, UNIX_EPOCH};
    let Some(home) = std::env::var_os("USERPROFILE").or_else(|| std::env::var_os("HOME")) else { return };
    let dir = std::path::PathBuf::from(home).join(".argo-tls");
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("argo-tls-debug.log");
    let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) else { return };
    let ts = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0);
    let _ = writeln!(f, "[t={ts}] {}", msg.as_ref());
}
```

### Step 4: 修 `client_dir()` USERPROFILE 兜底（W5 修复复制）

把 skyline `argo_tls.rs:65-66` 这两行：
```rust
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".argo-tls")
```

改为（仿 demo W5 + W4 §2 风格，加 `tls_log`）：
```rust
    let home = std::env::var_os("USERPROFILE")
        .or_else(|| std::env::var_os("HOME"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    let dir = home.join(".argo-tls");
    tls_log(format!("client_dir resolved dir={}", dir.display()));
    dir
```

确认 `PathBuf` 已在 skyline `argo_tls.rs` 顶部 import（应该已经在，因 demo 不需要新增 import；如未 import 则 ESCALATE）。

### Step 5: 在决策点埋点（仿 demo W4 §2 清单）

按 W8 §1 的 skyline 函数清单，在每个决策点加 `tls_log` 调用。**简化版**（不要求与 demo 完全一致，但关键决策点要覆盖）：

- `root_cert_resource_path` (line 13-22)：每候选路径 `tls_log(format!("root_cert_resource_path candidate={} hit={}", p.display(), hit))` + miss 时 `tls_log("root_cert_resource_path no_candidate_hit")`
- `load_client_identity` (line 73-90)：4 处 `?` 失败前各加 `tls_log` 记录原因（`crt_read_err=`、`key_read_err=`、`cert_pem_parse_err=`、`certs_empty`、`key_missing_in_pem=`、`key_parse_err=`），成功时 `tls_log("load_client_identity ok certs=1")`
- `client_identity_pem` (line 93-99)：read 失败前 `tls_log("crt_read_err/key_read_err")`
- `client_ca_cert_pem` (line 106-114)：`tls_log(format!("client_ca_cert_pem hit=ca_crt bytes={}", n))` / miss 时 `tls_log("client_ca_cert_pem miss=ca_crt")` + root.crt fallback 路径
- `apply_mtls` (line 132-158)：4 处 `format!("...{error}")` Err 出口前 `tls_log(format!("apply_mtls step=<step> err={:?}", error))`，成功时 `tls_log(format!("apply_mtls ok ca_loaded bytes={}", n))`
- `build_http_client` (line 165-173)：`tls_log(format!("build_http_client ok use_tls={}", use_tls))`，build 失败 `tls_log(format!("build_err use_tls={} err={:?}", use_tls, e))`
- `parse_allowed_gateway_url` (line 266-279)：4 处 reject 前 `tls_log(format!("reject_<reason> ..."))`，成功 `tls_log(format!("parse_allowed_gateway_url ok url={}", url))`
- `gateway_mtls_proxy` (line 289-333)：entry `tls_log(format!("gateway_mtls_proxy entry method= url={}", method, url))`，send 失败前 `tls_log(format!("send_err is_connect={} is_request={} is_timeout={} is_redirect={} err={:?}", ...))`，body read 失败 `tls_log("body_read_err")`，成功 `tls_log(format!("ok status={}", status))`

注意：skyline `argo_tls.rs` 与 demo 不完全一样（demo 行 1179/1417，skyline 574，结构精简）— 决策点对应位置请实际读代码定位，不要硬套 demo 行号。

### Step 6: 验证 cargo check

跑 `cargo check -p <skyline_package_name> --manifest-path /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/Cargo.toml`。`<skyline_package_name>` 从 `apps/skyline/src-tauri/Cargo.toml` 第 2 行 `[package] name="..."` 取。

应 <30s。失败则修编译错误。

## Output contract (Chinese, <400 words)

### 1. 改动文件 + 行号

`argo_tls.rs` — 列出 `tls_log` 函数插入位置 + `client_dir()` 修改前后 + N 处决策点埋点位置（按函数名 + 行号列）

### 2. `tls_log` 函数完整 body

Quote 实际写入的函数体

### 3. `client_dir()` 修改 diff

Before / After quote

### 4. 决策点埋点清单

按函数名列每个埋点的位置 + 事件名

### 5. `cargo check` 结果

用时 + 0 错误 / N 错误

### 6. ESCALATEs

如有

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (1 file only).
- Don't run cargo build/test/clippy.
- Don't run just dev.
- Don't modify `lib.rs`、`Cargo.toml`、JS 文件、`packages/gateway-client/`、`runtime_log/` 等。
- Don't add new crate deps.
- Don't try to do W8 推荐的 P1 方案 A/B（runtime_log 扩展、skyline_debug_log 新 channel）— 那需要改 lib.rs，超出本次 write-set。
- Don't git commit/push.
- Don't ask the user any questions.
