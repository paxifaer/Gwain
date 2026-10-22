# PROMPT-W5 — 修 `argo_tls.rs::client_dir()` Windows HOME bug (1 行 patch, kimi-k3, code edit, no tests)

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
  reason: surgical_bug_fix
  permission_mode: bypassPermissions
```

---

You are **W5** — a one-shot, **code-edit** worker. W2 已找到 TLS 失败根因：`argo_tls.rs:66-74` `client_dir()` 用 `std::env::var("HOME")`，Windows 下 `HOME` 不自动设置，回退到 `"."` 找不到 `.argo-tls/` → `apply_mtls` 立即 Err "mTLS client cert missing"。W2 离线 reqwest 探针用同一组证书 HTTP 200 成功，证明 cert/key/network/server 全健康。

W4 已加 `tls_log` + JS bug 修复（报告 `out-W4.log`），但**未修** `client_dir()` 本身的 HOME bug。W5 就是修这个 1 行 bug。

## CRITICAL: NO PARTIAL RETURNS

W5 任务极小（1 个文件、1-2 行改动）。直接做完并按输出契约报告，不要 status update。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W2.log` — W2 报告（根因 §7-8）
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W4.log` — W4 已落地的 tracing（确认 `tls_log` 已用 `USERPROFILE` 兜底模式）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- 单文件本地编辑，无 SSH。
- 不跑 cargo build/test/clippy（用户 just dev 自测）。
- 可跑一次 `cargo check -p SudoRobot`（应 <5s，因 W4 已 build 过）。

## Write-set (strictly bounded)

**只修这 1 个文件**：
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs`

**不动其他任何文件**。

## Step

### Read current `client_dir()`

读 `argo_tls.rs` line 60-100（找到 `pub fn client_dir()` 当前实现）。W2 报告 §7 quote 了它是这样：
```rust
pub fn client_dir() -> PathBuf {
    if let Ok(dir) = std::env::var(CLIENT_DIR_ENV) { ... }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".argo-tls")
}
```

先读确认当前代码是否还这样。

### Apply the fix

把 `std::env::var("HOME")` 改为优先 `USERPROFILE`（Windows）→ 然后 `HOME`（Linux/macOS）→ 最后 `"."` 兜底。最小改动：

```rust
let home = std::env::var("USERPROFILE")
    .or_else(|_| std::env::var("HOME"))
    .unwrap_or_else(|_| ".".to_string());
```

或更对称的 `var_os` 风格（与 W4 的 `tls_log` line 21 一致）：
```rust
let home = std::env::var_os("USERPROFILE")
    .or_else(|| std::env::var_os("HOME"))
    .map(std::path::PathBuf::from)
    .unwrap_or_else(|| std::path::PathBuf::from("."));
let _ = tls_log(format!("client_dir resolved home={}", home.display()));
PathBuf::from(home).join(".argo-tls")
```

任选一种。**必须**在 `client_dir()` 函数末尾（return 前）加一条 `tls_log` 调用记录解析出的路径（这样用户调试时能在 `argo-tls-debug.log` 看到 `client_dir resolved` 行）。

注意：`tls_log` 函数由 W4 已加在 `argo_tls.rs:16-46`，无需新增。直接调用即可。

### Verify (optional)

跑 `cargo check -p SudoRobot --manifest-path /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/Cargo.toml` 一次。应 <5s（W4 已编译过）。失败则修编译错误（但这是 1 行改动，几乎不会出错）。

## Output contract (Chinese, <200 words)

### 1. 改动文件 + 行号

`argo_tls.rs` line N-M — quote 修改前的代码 + 修改后的代码（diff 风格）

### 2. `cargo check` 结果（若跑）

用时 + 0 错误 / N 错误

### 3. ESCALATEs

如有

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (1 file only).
- Don't run cargo build/test/clippy.
- Don't run just dev.
- Don't modify any other file (including lib.rs, Cargo.toml, error.rs).
- Don't git commit/push.
- Don't add new crate deps.
- Don't ask the user any questions.
