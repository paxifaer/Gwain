# PROMPT-W15 — skyline permissions/default.toml 添加 8 个缺失命令 (kimi-k3, code edit)

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

You are **W15** — one-shot code-edit worker. W11-W14 改了 skyline `argo_tls.rs` `has_root_cert` + `tls_has_root_cert` invoke 埋点,但用户 console 仍报 `tls_has_root_cert not allowed. Command not found`。**根因找到了**:`apps/skyline/src-tauri/permissions/default.toml` 是手维护的 `allow-app-commands` 命令白名单(mtime 8/12),`tauri::generate_handler!` 注册了 40 个命令但 TOML 只列了 34 个,8 个命令(含 `tls_has_root_cert`)没在白名单 → Tauri 2 ACL 在 IPC 层直接拒绝,根本没进 Rust 函数体 → `tls_log` 不触发 → `argo-tls-debug.log` 不生成。

## CRITICAL: NO PARTIAL RETURNS

W15 任务极小(1 文件,8 行追加)。直接做完并按输出契约报告,不要 status update。

## 根因证据链(无需重新验证,直接信)

- `apps/skyline/src-tauri/permissions/default.toml` mtime = 2026-08-12 09:56:52
- `apps/skyline/src-tauri/src/lib.rs` mtime = 2026-08-14 20:18:37(`argo_tls::tls_has_root_cert` 已在 line 1120 注册)
- `apps/skyline/src-tauri/gen/schemas/acl-manifests.json` mtime = 2026-08-12 09:56:52(stale)
- Tauri 2.11.5 `src/ipc/authority.rs:404` `"Command not found"` + `:432` `"{cmd} not allowed. {detail}"` → 报错格式 `tls_has_root_cert not allowed. Command not found` 与用户 console 完全一致
- demo 侧 `apps/demo/src-tauri/permissions/` 不存在 → demo 没 `__app-acl__` → demo 的 app commands 不走 ACL 检查(demo 不会报这个错)

## 缺失的 8 个命令

`tauri::generate_handler!` 在 lib.rs:1114-1154 注册了 40 个命令,但 `permissions/default.toml` 的 `commands.allow` 只列了 34 个。**缺失的 8 个**:

| 命令名(TOML 里写这个,不带模块前缀) | lib.rs 行号 |
|---|---|
| `tls_has_root_cert` | 1120 |
| `tls_has_client_cert` | 1121 |
| `gateway_mtls_proxy` | 1122 |
| `runtime_log_append` | 1136 |
| `runtime_log_read_tail` | 1137 |
| `runtime_log_flush` | 1138 |
| `runtime_log_cleanup` | 1139 |
| `chatbot_agent_materialize_taskflow_template` | 1140 |

## Write-set (strictly bounded)

**只修这 1 个文件**:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/permissions/default.toml`

**不动**其他文件,包括 `argo_tls.rs` / `lib.rs` / `main.rs` / JS / Cargo.toml / `capabilities/default.json` / `gen/schemas/*` 等。

## Steps

### Step 1: 读现状

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/permissions/default.toml`,确认当前 `commands.allow` 列表是 34 个命令,**不包含**上述 8 个缺失命令。

### Step 2: 追加 8 个命令

在 `commands.allow` 列表末尾(`"skyline_updater_install",` 之后,闭合 `]` 之前)追加这 8 行(每行 2 空格缩进 + 双引号 + 命令名 + 逗号):

```toml
  "tls_has_root_cert",
  "tls_has_client_cert",
  "gateway_mtls_proxy",
  "runtime_log_append",
  "runtime_log_read_tail",
  "runtime_log_flush",
  "runtime_log_cleanup",
  "chatbot_agent_materialize_taskflow_template",
```

**注意**:不要动其他既有命令,不要删除 `chatbot_agent_build_turn_ready` / `chatbot_agent_run_turn`(这俩在 TOML 但不在 `generate_handler!`,可能是 stale,但留着不影响功能,本 prompt 不要求清理)。

### Step 3: 验证 TOML 语法

跑 `python3 -c "import tomllib; tomllib.load(open('/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/permissions/default.toml','rb'))"` 验证 TOML 语法正确(0 异常 = OK)。

如果系统没 tomllib(py3.10-),用 `python3 -c "import tomli; tomli.load(open('...','rb'))"` 或 `cargo run --manifest-path .../Cargo.toml --quiet || true` 跳过(本 prompt 不要求 cargo build)。

### Step 4: scp 同步到 windev2

```bash
scp /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/permissions/default.toml windows_dev_2:D:/code/dang/robot-app-platform/apps/skyline/src-tauri/permissions/default.toml
```

### Step 5: 删除 windev2 stale acl-manifests.json(强制 tauri-build 重生成)

```bash
ssh windows_dev_2 'powershell -NoProfile -Command "Remove-Item -Force D:\code\dang\robot-app-platform\apps\skyline\src-tauri\gen\schemas\acl-manifests.json -ErrorAction SilentlyContinue; Test-Path D:\code\dang\robot-app-platform\apps\skyline\src-tauri\gen\schemas\acl-manifests.json"'
```

应输出 `False`(文件已删)。

### Step 6: 同步删除 Linux 侧 stale acl-manifests.json

```bash
rm -f /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/gen/schemas/acl-manifests.json
```

### Step 7: 验证 scp 同步

```bash
ssh windows_dev_2 'powershell -NoProfile -Command "Get-Content D:\code\dang\robot-app-platform\apps\skyline\src-tauri\permissions\default.toml | Select-String -Pattern \"tls_has_root_cert|gateway_mtls_proxy|runtime_log_append\" | Measure-Object | Select-Object -ExpandProperty Count"'
```

应输出 `3`(3 个 grep 命中 = 3 个新命令都在)。

## Output contract (Chinese, <300 words)

### 1. 改动文件 + 行号

`permissions/default.toml` — 修改前 N 行 → 修改后 N+8 行 + diff 片段(只显示追加的 8 行)

### 2. 修改后 `commands.allow` 末尾 10 行 quote

带行号,显示追加的 8 行 + 上下文

### 3. TOML 语法验证结果

`tomllib.load` 0 异常 / 异常信息

### 4. scp 同步验证

windev2 `default.toml` LastWriteTime + grep `tls_has_root_cert|gateway_mtls_proxy|runtime_log_append` 命中数(应 = 3)

### 5. stale acl-manifests.json 删除验证

Linux 侧 + windev2 侧 `Test-Path` 都应 = `False`

### 6. ESCALATEs

如有

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (1 file only).
- Don't run cargo build/check/test/clippy。
- Don't run just dev。
- Don't restart services or kill processes。
- Don't git commit/push。
- Don't ask the user any questions。
- Don't modify `argo_tls.rs` / `lib.rs` / `main.rs` / JS / Cargo.toml / `capabilities/default.json` / `gen/schemas/*` / `permissions/autogenerated/*` 等不在 write-set 的文件。
- Don't 删除 `chatbot_agent_build_turn_ready` / `chatbot_agent_run_turn`(stale 但不影响功能,本 prompt 不要求清理)。
- Don't use PowerShell -EncodedCommand with UTF-8 base64 (PowerShell 需要 UTF-16LE base64)。
