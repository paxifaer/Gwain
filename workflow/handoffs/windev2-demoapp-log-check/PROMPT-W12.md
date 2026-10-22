# PROMPT-W12 — demo argo_tls.rs has_root_cert mirror W11 fix (kimi-k3, code edit)

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

You are **W12** — one-shot code-edit worker. W11 确认 skyline `argo_tls.rs:89-91` `has_root_cert` 独立路径 bug(只查 embedded `root.crt`,不查 `<client_dir>/ca.crt`)→ 用户 windev2 `~/.argo-tls/ca.crt` 已部署但代码看不到 → UI 误报"本机缺 root CA 证书"。W11 已修 skyline。**demo 侧 `argo_tls.rs:89-91` 与 skyline 修复前一字不差**,需要 mirror 同款 fix。

## CRITICAL: NO PARTIAL RETURNS

W12 任务极小(1 文件,3 行改 15 行)。直接做完并按输出契约报告,不要 status update。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W11.log` — W11 报告(含 skyline 修复 diff + 验证)
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Write-set (strictly bounded)

**只修这 1 个文件**:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs`

**不动**其他文件,包括 lib.rs、main.rs、JS、Cargo.toml、skyline 任何文件、`packages/gateway-client/` 等。

## Steps

### Step 1: 读 W11 skyline 修复模板

读 `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W11.log` §6,quote skyline `has_root_cert` 修复后的完整函数体(15 行):
```rust
pub fn has_root_cert(app: &AppHandle) -> bool {
    let (_, _, ca_path) = build_cert_paths();
    if ca_path.exists() {
        tls_log(format!("has_root_cert hit=ca_crt path={}", ca_path.display()));
        return true;
    }
    tls_log(format!("has_root_cert miss=ca_crt path={}", ca_path.display()));
    let embedded = load_root_cert(app).is_some();
    tls_log(format!("has_root_cert embedded={embedded}"));
    embedded
}
```

### Step 2: 读 demo argo_tls.rs:89-91 现状

确认 demo `argo_tls.rs:89-91` 当前是:
```rust
pub fn has_root_cert(app: &AppHandle) -> bool {
    load_root_cert(app).is_some()
}
```

确认 demo `argo_tls.rs:93-100` `build_cert_paths()` 已存在(返回 `(crt_path, key_path, ca_path)`,第三个元素 = `client_dir/ca.crt`)。

确认 demo `argo_tls.rs:8-41` `tls_log` 已存在(W4 已加)。

### Step 3: 应用 mirror fix

把 demo `argo_tls.rs:89-91` 这 3 行替换为 W11 skyline 修复版 15 行(§1 quote)。

### Step 4: cargo check

跑 `cargo check -p <demo_package_name> --manifest-path /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/Cargo.toml`。`<demo_package_name>` 从 `apps/demo/src-tauri/Cargo.toml` 第 2 行 `[package] name="..."` 取。

应 <30s。失败则修编译错误。

### Step 5: scp 同步到 windev2

```bash
scp apps/demo/src-tauri/src/argo_tls.rs windows_dev_2:D:/code/dang/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs
```

验证 windev2 上的 argo_tls.rs 改动到位(grep `has_root_cert hit=ca_crt`)。

## Output contract (Chinese, <300 words)

### 1. 改动文件 + 行号

demo argo_tls.rs — `has_root_cert` 修改前 line 89-91 → 修改后 line 89-101(或实际行号)+ diff 片段

### 2. `has_root_cert` 修改后完整 body quote

### 3. cargo check 结果

用时 + 0 错误 / N 错误

### 4. scp 同步验证

windev2 argo_tls.rs LastWriteTime + grep `has_root_cert hit=ca_crt` 命中数

### 5. ESCALATEs

如有

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (1 file only).
- Don't run cargo build/test/clippy(cargo check 可以）.
- Don't run just dev.
- Don't restart services or kill processes.
- Don't git commit/push.
- Don't ask the user any questions.
- Don't modify skyline 任何文件 / lib.rs / main.rs / JS / Cargo.toml / packages/gateway-client/.
