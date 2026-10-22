# PROMPT-W13 — skyline "本机缺 rootCA 证书" 修复后仍报警告:windev2 环境跨平台审计 (kimi-k3, debug+fix)

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

You are **W13** — diagnose why skyline "本机缺 rootCA 证书" warning persists after W11 fix + `just dev-tauri-skyline` recompile. 用户怀疑 windev2 环境与 Linux 不一致,代码没考虑跨平台。

## 背景

- W11 已修 skyline `argo_tls.rs:89-91` `has_root_cert` — 改为先查 `build_cert_paths()` 返回的 `<client_dir>/ca.crt`,再 fallback embedded `root.crt`
- W11 已 scp 到 windev2 7:45 PM,已 cargo check 0 错误
- 用户跑 `just dev-tauri-skyline` 重编译 + 启动 skyline,**警告依然出现**
- 用户 windev2 `C:\Users\jack\.argo-tls\ca.crt` 已部署(8/18 4:05 PM)
- W10 修复 `client_dir()` 用 USERPROFILE 优先,HOMO 兜底 — Linux 工位 + windev2 都已验证

**Hypothesis 1**:用户跑的 `just dev-tauri-skyline` 没真正重编译(增量编译跳过),binary 还是 7:28 PM 老版本
**Hypothesis 2**:`client_dir()` 在 windev2 上返回了非 `C:\Users\jack\.argo-tls\` 的路径(跨平台 bug),导致 `ca_path.exists()` false
**Hypothesis 3**:UI 警告来源不止 `tls_has_root_cert` — 可能还有别的检查路径(如 `tls_has_client_cert` 或 JS 侧独立逻辑)
**Hypothesis 4**:`build_cert_paths()` 在 Windows 下有别的跨平台问题(路径分隔符、env var case sensitivity)

## CRITICAL: NO PARTIAL RETURNS

诊断完成后,如发现代码 bug 在 write-set 内,直接修。3-min no-response = ESCALATE。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W11.log` — W11 修复报告(含 has_root_cert 新实现 + scp 验证)
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W10.log` — W10 修复报告(client_dir USERPROFILE 兜底)
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- windev2 SSH: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`,引号嵌套 pain 用 base64
- 单条 SSH ≤25s
- 3-min no-response = ESCALATE

## Write-set (bounded)

**最多修这 3 个文件**:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/main.rs`

**不动**其他文件,包括 JS、Cargo.toml、`packages/gateway-client/` 等。

## Checks

### A. windev2 skyline binary 时间戳 + argo-tls-debug.log

SSH windev2:
1. skyline 进程:`Get-Process | Where-Object { $_.ProcessName -match "SkylineStudio|skyline" }` — PID + StartTime + Path
2. binary 时间戳:`Get-Item D:\code\dang\robot-app-platform\apps\skyline\src-tauri\target\debug\SkylineStudio.exe | Select-Object LastWriteTime,Length` — 是否晚于 argo_tls.rs 7:45 PM?
3. argo_tls.rs 时间戳:`Get-Item D:\code\dang\robot-app-platform\apps\skyline\src-tauri\src\argo_tls.rs | Select-Object LastWriteTime,Length` — 验证 W11 修复在
4. argo-tls-debug.log:`Get-Content C:\Users\jack\.argo-tls\argo-tls-debug.log -Tail 30` — skyline 启动后是否有新条目?特别看:
   - `client_dir resolved dir=...` — windev2 上 `client_dir()` 返回什么路径?
   - `has_root_cert hit=ca_crt path=...` 或 `has_root_cert miss=ca_crt path=...` — fix 是否被触发?
   - `has_root_cert embedded=...` — fallback embedded root.crt 是否 hit?

**判断 1**:binary 时间戳晚于 argo_tls.rs 7:45 PM → 重新编译成功
**判断 2**:argo-tls-debug.log 有 `has_root_cert` 条目 → W11 fix 已在新 binary 中运行
**判断 3**:log 显示 `has_root_cert miss=ca_crt path=C:\Users\jack\.argo-tls\ca.crt` 但文件确实存在 → 跨平台 bug(`Path::exists()` 在 Windows 下行为异常?或 path 字符串解析错?)
**判断 4**:log 显示 `client_dir resolved dir=...` 是非 `C:\Users\jack\.argo-tls\` 路径 → `client_dir()` 跨平台 bug
**判断 5**:log 显示 `has_root_cert embedded=true` → fallback 已命中,UI 不应再警告 → JS 侧有别的检查路径

### B. 验证 `C:\Users\jack\.argo-tls\ca.crt` 文件存在 + 可读

```powershell
Get-ChildItem C:\Users\jack\.argo-tls\ | Select-Object Name,Length,LastWriteTime
```

确认 ca.crt 文件:
1. 存在
2. 大小 > 0
3. 可读(`Get-Content C:\Users\jack\.argo-tls\ca.crt -Raw | Select-Object -First 1 | ForEach-Object { $_.Substring(0, [Math]::Min(50, $_.Length)) }` — 应看到 `-----BEGIN CERTIFICATE-----`)

### C. 读 skyline `argo_tls.rs` 当前 `client_dir()` + `build_cert_paths()` + `has_root_cert()` 实现

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs` 顶部 200 行,quote:
1. `client_dir()` 完整 body(行号)— 验证 W10 USERPROFILE 兜底在
2. `build_cert_paths()` 完整 body(行号)— 看是否调 `client_dir()`
3. `has_root_cert()` 完整 body(行号)— 验证 W11 fix 在

**关键审计**:
- `client_dir()` 是否在 Windows 下能正确读 `USERPROFILE`?
- `build_cert_paths()` 第三返回值 = `dir.join(CLIENT_CA_NAME)`,其中 `CLIENT_CA_NAME = "ca.crt"` — Windows 路径分隔符 `Path::join` 是否正确处理?
- `has_root_cert` 的 `ca_path.exists()` 在 Windows 下是否有 case sensitivity 问题?

### D. 跨平台审计 — 读其他可能检查 root cert 的代码路径

grep skyline `argo_tls.rs` + `lib.rs` 找其他可能返回 false 让 UI 警告的检查:

```bash
grep -n "root_cert\|ca_crt\|ca_cert\|rootCA\|ROOT_CA" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs
grep -n "root_cert\|ca_crt\|ca_cert\|rootCA\|ROOT_CA\|tls_has" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs
```

看是否有别的 Tauri 命令(如 `tls_has_client_cert`、`check_tls_readiness` 等)也独立检查 cert,且没走 `client_dir()`。

### E. skyline 前端 UI 警告文案来源(W11 §5 已查,复核)

W11 §5 报告警告文案在:
- `apps/skyline/src/features/projects/workspace/workspaceTaskflowMessages.ts:2304-2307` `WORKSPACE_REAL_GATEWAY_SERVER_TLS_HINT_ROOT_CA_MISSING`
- 渲染点 `RealGatewayServerAddressField.tsx:118-131`(当 `protocol === "https"` 且 `rootCertAvailable === false`)
- `services/argo-tls.ts:3-5` 调 `tls_has_root_cert`

读 `RealGatewayServerAddressField.tsx:100-140` + `services/argo-tls.ts` 全文,看:
1. JS 怎么调 `tls_has_root_cert`?是否有缓存?
2. JS 是否还有别的检查(如同时调 `tls_has_client_cert` 并 OR 起来)?
3. `rootCertAvailable` 状态如何更新?是否有 stale state 问题?

### F. 直接在 windev2 跑 `tls_has_root_cert` Tauri 命令(绕过 UI)

如果 skyline 进程在跑,可以直接 invoke Tauri 命令测试(用 `curl` 打 Tauri 的 IPC port 太复杂,跳过)。

替代方案:让用户在 skyline dialog 里再点一次触发 `hasRootCert()` — 但用户已报警告仍在,说明 `hasRootCert()` 返回 false。所以重点是看 log 里 `has_root_cert` 的事件路径。

**如果 argo-tls-debug.log 没有 `has_root_cert` 条目**:
- 说明 UI 调的不是新 `has_root_cert`(可能 JS 缓存了旧 invoke 结果?)
- 或新 binary 还没启动(W11 fix 还没编译进去)
- 或 UI 根本没调 `tls_has_root_cert`(可能调了别的命令,如 `tls_has_client_cert` 或 `check_tls_readiness`)

### G. 决定修复方案

基于 A-F 诊断:

**情况 1**:`just dev-tauri-skyline` 没真正重编译(binary 还是 7:28 PM) → 用户跑的命令有问题,可能 windev2 上 `just` 没装 / 跑错目录 / 增量编译跳过。**不修代码**,报告 + 让用户 `cargo clean` 后重跑

**情况 2**:binary 已更新(晚于 7:45 PM),argo-tls-debug.log 有 `has_root_cert miss=ca_crt path=C:\Users\jack\.argo-tls\ca.crt` 但文件确实存在 → 跨平台 `Path::exists()` bug。深入查 `client_dir()` 在 Windows 下返回值是否含奇怪字符(BOM? 反斜杠转义?)。修 `argo_tls.rs`

**情况 3**:binary 已更新,log 有 `has_root_cert embedded=true` → Rust 侧返回 true,但 UI 仍警告 → JS 侧有别的检查路径或 stale state。**JS 在 write-set 之外,ESCALATE**

**情况 4**:UI 调的不是 `tls_has_root_cert`,而是别的命令(如 `check_tls_readiness` 或 `tls_has_client_cert`)→ 该命令有独立 bug。修对应命令实现(在 write-set 内)

**情况 5**:binary 已更新,argo-tls-debug.log 完全没有 `has_root_cert` 条目 → `tls_has_root_cert` 命令根本没被调 → JS 没调它,或调了但 invoke 失败。**查 JS 调用链**,JS 在 write-set 外,ESCALATE

### H. 应用修复(仅在情况 2/4 需要)

修完跑 `cargo check -p SkylineStudio --manifest-path apps/skyline/src-tauri/Cargo.toml` 验证编译通过。

### I. 同步到 windev2

如果修了文件,scp 到 windev2 + 验证 LastWriteTime。

## Output contract (Chinese, <700 words)

### 1. 诊断结果

情况 1/2/3/4/5 哪一个?引用具体证据(binary 时间戳 + log 内容 + 代码片段)

### 2. windev2 skyline 进程状态 + binary 时间戳

PID + StartTime + Path + binary LastWriteTime + argo_tls.rs LastWriteTime

### 3. argo-tls-debug.log 最新条目

tail 30 行 quote + 标注 `has_root_cert` / `client_dir resolved dir=` / `embedded=` 等关键事件

### 4. `C:\Users\jack\.argo-tls\ca.crt` 文件状态

存在 + 大小 + 首 50 字符(应 `-----BEGIN CERTIFICATE-----`)

### 5. skyline `argo_tls.rs` `client_dir()` + `build_cert_paths()` + `has_root_cert()` 完整 body quote

带行号

### 6. JS 调用链复核

`RealGatewayServerAddressField.tsx` 触发条件 + `services/argo-tls.ts` 完整内容 + 是否有别的检查路径

### 7. 跨平台审计

`client_dir()` 在 Windows 下是否能正确读 USERPROFILE?有无 case sensitivity / 路径分隔符 / BOM 问题?有无别的 Tauri 命令独立检查 cert?

### 8. 修复内容(如适用)

- 修了哪个文件 + 哪些行 + diff 片段
- cargo check 结果
- scp 同步验证

### 9. ESCALATEs

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
