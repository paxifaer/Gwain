# PROMPT-W14 — skyline tls_has_root_cert invoke 诊断埋点 + windev2 frontend 同步审查 (kimi-k3, debug+fix)

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
  reason: debug_and_fix
  permission_mode: bypassPermissions
```

---

You are **W14** — diagnose why `tls_has_root_cert` Tauri command is never invoked on windev2 skyline, even though W11 fix is in the binary and the skyline process is running.

## 背景

- W11 已修 skyline `argo_tls.rs:89-91` `has_root_cert` (W11 fix scp 到 windev2 7:45 PM)
- W13 确认 binary 7:46:01 PM 含 W11 fix 标记 (strings 扫描),进程 PID 23164 StartTime 8:04:55 PM 在跑
- **但 `C:\Users\jack\.argo-tls\argo-tls-debug.log` 不存在** → `tls_log` 从未被触发 → `tls_has_root_cert` 命令从未被 invoke
- USERPROFILE 和 HOME 都 = `C:\Users\jack` ✓
- ca.crt 在 `C:\Users\jack\.argo-tls\` (615 字节, 4:05 PM 部署) ✓
- skyline 进程 CommandLine = `"target\debug\SkylineStudio.exe"` (直接跑 binary,不是 dev 模式 wrapper)
- port 1420 没人 listen → vite dev server 没在跑 → binary 加载内嵌 frontend bundle
- 没有 node/bun 进程在跑

**Hypothesis 1**: JS invoke 在 Tauri 边界失败,被 `.catch(console.warn)` 静默吞错,初始 `useState(false)` 保留 → UI 显示警告
**Hypothesis 2**: windev2 上 frontend 代码与 Linux 不同步 — `services/argo-tls.ts` 或 dialog 组件缺失 `hasRootCert()` 调用,或调的命令名不一样
**Hypothesis 3**: binary 内嵌的 frontend bundle 是旧版本(上次 `cargo build` 时打包),不含 `hasRootCert()` 调用
**Hypothesis 4**: 用户没真正打开 RealGatewayServerDialog — `useEffect` 只在 dialog open 时调 `hasRootCert()`

## CRITICAL: NO PARTIAL RETURNS

诊断完成后,如发现代码 bug 在 write-set 内,直接修。3-min no-response = ESCALATE。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W11.log` — W11 修复报告
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W13.log` — W13 诊断报告(binary 含 fix 但 log 不存在)
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- windev2 SSH: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`,引号嵌套 pain 用 base64(注意 PowerShell -EncodedCommand 需要 UTF-16LE base64,不是 UTF-8)
- 单条 SSH ≤25s
- 3-min no-response = ESCALATE

## Write-set (bounded)

**最多修这 3 个文件**:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/main.rs`

**不动**其他文件,包括 JS、Cargo.toml、`packages/gateway-client/` 等。

## Checks

### A. windev2 skyline frontend 代码同步状态

SSH windev2 验证 frontend 代码是否与 Linux 工位一致:

1. `Get-Content D:\code\dang\robot-app-platform\apps\skyline\src\services\argo-tls.ts` — 应该是:
   ```typescript
   import { invokeTauri } from "./tauri-invoke";
   export async function hasRootCert(): Promise<boolean> {
     return await invokeTauri<boolean>("tls_has_root_cert");
   }
   export async function hasClientCert(): Promise<boolean> {
     return await invokeTauri<boolean>("tls_has_client_cert");
   }
   ```
   文件 LastWriteTime?如果早于 8/18 7:45 PM → windev2 frontend 没跟 Linux 同步

2. `Get-Content D:\code\dang\robot-app-platform\apps\skyline\src\features\projects\workspace\RealGatewayServerDialog.tsx | Select-String -Pattern "hasRootCert|rootCertAvailable" | Select-Object -First 10` — 验证 dialog 调 `hasRootCert()`

3. `Get-Content D:\code\dang\robot-app-platform\apps\skyline\src-tauri\src\argo_tls.rs | Select-String -Pattern "has_root_cert hit|tls_has_root_cert"` — 验证 W11 fix 在 windev2 Rust 源码中

### B. skyline binary 内嵌 frontend bundle 是否含 `hasRootCert` 调用

binary 是 7:46 PM 编译的,内嵌的 frontend bundle 来自 `apps/skyline/dist/`。验证:

1. `Test-Path D:\code\dang\robot-app-platform\apps\skyline\dist\` — dist 目录是否存在?
2. `Get-ChildItem D:\code\dang\robot-app-platform\apps\skyline\dist\` — dist 内容 + 时间戳
3. 如果 dist 存在,`Select-String -Path D:\code\dang\robot-app-platform\apps\skyline\dist\assets\*.js -Pattern "hasRootCert|tls_has_root_cert" | Select-Object -First 5` — 验证 frontend bundle 含 `hasRootCert` 调用

**判断**:
- 如果 dist 不存在或不含 `hasRootCert` → binary 加载的是空 frontend 或旧 frontend → 用户需要先 `bun run build` 生成 dist 再 `just dev-tauri-skyline`
- 如果 dist 含 `hasRootCert` → JS 应该调 invoke,问题在 invoke 边界失败

### C. skyline binary strings 扫描 `tls_has_root_cert` 命令注册

```powershell
$bytes = [System.IO.File]::ReadAllBytes("D:\code\dang\robot-app-platform\apps\skyline\src-tauri\target\debug\SkylineStudio.exe")
$text = [System.Text.Encoding]::ASCII.GetString($bytes)
if ($text -match "tls_has_root_cert") { Write-Host "FOUND: tls_has_root_cert in binary" } else { Write-Host "MISSING: tls_has_root_cert not in binary" }
if ($text -match "has_root_cert hit=ca_crt") { Write-Host "FOUND: has_root_cert hit=ca_crt (W11 fix)" } else { Write-Host "MISSING: W11 fix not in binary" }
```

验证 binary 含 Tauri 命令注册 + W11 fix 标记。

### D. skyline 进程 env vars + parent process

```powershell
$proc = Get-Process -Id 23164 -ErrorAction SilentlyContinue
if ($proc) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=23164" | Select-Object ParentProcessId,CommandLine
    Write-Host "PID 23164 ParentPid: $($parent.ParentProcessId)"
    Write-Host "CommandLine: $($parent.CommandLine)"
    $parentProc = Get-Process -Id $parent.ParentProcessId -ErrorAction SilentlyContinue
    if ($parentProc) { Write-Host "Parent Name: $($parentProc.ProcessName)" } else { Write-Host "Parent process exited" }
}
```

看 skyline 进程的 parent — 如果 parent 已退出,说明用户跑 `just dev-tauri-skyline` 后 just 退出了,binary 自己继续跑(Tauri dev 模式下 binary 应该是 just 的子进程,just 退出 binary 应该跟着退;如果不是,可能用户直接跑了 binary)。

### E. 在 Rust 侧 `tls_has_root_cert` 命令入口加埋点

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs:267-270`:

```rust
#[tauri::command]
pub async fn tls_has_root_cert(app: AppHandle) -> Result<bool, String> {
    Ok(has_root_cert(&app))
}
```

改为加 `tls_log` 埋点确认 invoke 是否到达:

```rust
#[tauri::command]
pub async fn tls_has_root_cert(app: AppHandle) -> Result<bool, String> {
    tls_log("tls_has_root_cert invoked");
    let result = has_root_cert(&app);
    tls_log(format!("tls_has_root_cert result={result}"));
    Ok(result)
}
```

同样在 `tls_has_client_cert` (line 272-275) 加埋点:
```rust
#[tauri::command]
pub fn tls_has_client_cert() -> bool {
    tls_log("tls_has_client_cert invoked");
    load_client_identity().is_some()
}
```

### F. cargo check + scp

```bash
cargo check -p SkylineStudio --manifest-path apps/skyline/src-tauri/Cargo.toml
scp apps/skyline/src-tauri/src/argo_tls.rs windows_dev_2:D:/code/dang/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs
```

验证 windev2 argo_tls.rs LastWriteTime 更新 + 含 `tls_has_root_cert invoked` 字符串。

### G. 不重新编译 binary

用户需要自己跑 `just dev-tauri-skyline` 让新埋点进入 binary。W14 不跑 just dev。

## Output contract (Chinese, <700 words)

### 1. 诊断结果

Hypothesis 1/2/3/4 哪一个最可能?引用具体证据

### 2. windev2 skyline frontend 代码同步状态

`argo-tls.ts` LastWriteTime + 内容 quote + 是否与 Linux 一致

### 3. dist 目录 + frontend bundle 状态

dist 是否存在 + 时间戳 + bundle 是否含 `hasRootCert` 字符串

### 4. binary strings 扫描结果

`tls_has_root_cert` 命令注册 + W11 fix 标记是否在 binary 中

### 5. skyline 进程 parent + CommandLine

PID 23164 的 parent 进程(是否 just/cargo/node,或已退出)

### 6. 修复内容(如适用)

- 修了哪个文件 + 哪些行 + diff 片段
- cargo check 结果
- scp 同步验证

### 7. 用户下一步验证

用户需要:
1. 跑 `just dev-tauri-skyline` 重新编译(让新埋点进入 binary)
2. 启动 skyline,打开 RealGatewayServerDialog
3. 查 `C:\Users\jack\.argo-tls\argo-tls-debug.log`
4. 如果 log 含 `tls_has_root_cert invoked` → invoke 到达 Rust,问题在 `has_root_cert` 函数本身
5. 如果 log 仍不生成 → invoke 在 JS↔Rust 边界失败,需查 JS(超出 write-set,ESCALATE)

### 8. ESCALATEs

所有未做的检查、判断分歧、超出 write-set 的修复需求

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (3 files max).
- Don't run cargo build/test/clippy（cargo check 可以）.
- Don't run just dev.
- Don't restart services or kill processes.
- Don't git commit/push.
- Don't ask the user any questions.
- Don't modify JS / Cargo.toml / packages/gateway-client/ 等不在 write-set 的文件.
- Don't use PowerShell -EncodedCommand with UTF-8 base64 (PowerShell 需要 UTF-16LE base64,否则会乱码失败).
