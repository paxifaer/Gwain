# PROMPT-W11 — skyline "本机缺 rootCA 证书" 警告诊断 + 修复 (kimi-k3, code edit)

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

You are **W11** — diagnose + fix worker. 用户重新打开 skyline studio 界面后看到警告：

> **直连机器人界面警告：本机缺 rootCA 证书，连接将失败**

背景：
- demo app (W4+W5 修复) 已验证 TLS 通了，status=200
- skyline studio (W10 复制 W4+W5 P0) 已在 Linux 工作站改完 + scp 同步到 windev2（argo_tls.rs 762 行, USERPROFILE×2, tls_log×39 验证通过）
- 用户应该在 windev2 上 `just dev-tauri-skyline` 重编译 + 启动后看到这个警告

**Hypothesis**：skyline `lib.rs` 的 `tls_has_root_cert` Tauri 命令（W8 §4 line 1120-1122 提到）独立调用某路径检查，**不走 `argo_tls.rs::client_dir()`**，所以 W10 修复对它无效。或者用户跑的还是老 binary（代码没更新）。

## CRITICAL: NO PARTIAL RETURNS

诊断完成后，如发现是代码 bug 在 write-set 内，直接修。不要 status update。3-min no-response = ESCALATE。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W8.log` — W8 skyline 审查（§4 lib.rs `tls_has_root_cert` 在 line 1120-1122）
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W10.log` — W10 报告（skyline argo_tls.rs 已加 tls_log + USERPROFILE）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- windev2 SSH: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`，引号嵌套 pain 用 base64
- 单条 SSH ≤25s
- 3-min no-response = ESCALATE

## Write-set (bounded)

**最多修这 3 个文件**（实际可能只需 1 个）：
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/argo_tls.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/main.rs`

**不动**其他文件，包括 JS、Cargo.toml、`packages/gateway-client/` 等。

## Checks

### A. windev2 skyline 进程状态 + argo-tls-debug.log

SSH windev2 检查：
1. skyline 进程：`Get-Process | Where-Object { $_.ProcessName -match "SkylineStudio|skyline" }` — PID + StartTime + Path
2. argo-tls-debug.log：`Get-Content C:\Users\jack\.argo-tls\argo-tls-debug.log -Tail 50` — 是否有 skyline 启动后的新条目？特别注意 `client_dir resolved dir=...` 行
3. windev2 skyline argo_tls.rs：`Get-Content D:\code\dang\robot-app-platform\apps\skyline\src-tauri\src\argo_tls.rs | Select-String -Pattern "USERPROFILE|tls_log"` — 验证 W10 修复在 windev2 上还在

**判断 1**：如果 skyline 进程 Path 是 `target\debug\SkylineStudio.exe`（或类似）且 StartTime 是用户最近重启时间，且 argo-tls-debug.log 有新 skyline 条目 → 代码已更新
**判断 2**：如果 argo_tls.rs 没有 USERPROFILE → 代码被回滚或没 scp 成功
**判断 3**：如果 argo-tls-debug.log 有 `client_dir resolved dir=C:\Users\jack\.argo-tls` → W10 修复在 skyline 也生效
**判断 4**：如果 argo-tls-debug.log 有 `client_dir resolved dir=.\argo-tls` 或类似错误路径 → W10 修复未生效（用户跑老 binary 或代码没更新）

### B. skyline `lib.rs` `tls_has_root_cert` 命令实现

读 `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src-tauri/src/lib.rs` 中 `tls_has_root_cert` 和 `tls_has_client_cert` 命令实现。W8 §4 说在 line 1120-1122 附近。

关键查：
1. 这两个命令怎么检查证书存在？
2. 它们调 `argo_tls.rs::client_dir()` 吗？还是用独立路径逻辑？
3. 如果独立路径逻辑，是否有同样的 HOME bug（`std::env::var("HOME")` 无 USERPROFILE 兜底）？
4. 它们调 `argo_tls.rs::client_ca_cert_pem()` 或类似函数吗？那些函数 W10 是否覆盖到了？

### C. skyline 前端警告文案来源

grep skyline 前端代码找"缺 rootCA"或"rootCA 证书"或类似文案：

```bash
grep -rni "缺.*rootCA\|rootCA.*缺\|rootCA.*证书\|缺少.*CA\|本机.*缺" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/
```

也 grep `tls_has_root_cert` 在 JS 侧的调用：

```bash
grep -rn "tls_has_root_cert\|tls_has_client_cert" /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/
```

找到警告文案后：
1. quote 文案所在文件 + 行号 + 周围 5 行
2. 看 JS 调 `tls_has_root_cert` 后如何处理 false 返回值
3. 是否有 i18n catalog 条目（CLAUDE.md 提到 skyline 用 Lingui）

### D. skyline 前端是否也调 `argo-tls-debug.log` 写入路径

`argo-tls-debug.log` 是 W4 在 `argo_tls.rs::tls_log` 里写的。skyline 前端是否调 Tauri 命令导致 `argo_tls.rs` 中的函数被调用 → 触发 `tls_log`？或者 skyline 启动时只调 `tls_has_root_cert`，而 `tls_has_root_cert` 实现里没调 `argo_tls.rs` 中带 `tls_log` 的函数？

如果 `tls_has_root_cert` 命令的实现在 `lib.rs` 中独立写（不调 `argo_tls.rs::client_ca_cert_pem`），那 W10 加的 `tls_log` 不会在 `tls_has_root_cert` 路径上触发，argo-tls-debug.log 不会有这条命令的记录。

### E. 决定修复方案

基于 A-D 的诊断：

**情况 1**：代码已更新（windev2 argo_tls.rs 有 USERPROFILE），但 `tls_has_root_cert` 命令在 `lib.rs` 中用独立路径逻辑（也有 HOME bug）→ **修 `lib.rs` 让 `tls_has_root_cert` 改调 `argo_tls.rs::client_dir()` 或 `argo_tls.rs::client_ca_cert_pem()`，复用 W10 修复**

**情况 2**：代码没更新（windev2 argo_tls.rs 无 USERPROFILE）→ 用户跑老 binary 或 scp 失败。**不修代码**，直接报告 + 让用户重新 scp + 重启

**情况 3**：`tls_has_root_cert` 调 `argo_tls.rs::client_dir()` + W10 修复生效，但 UI 仍警告 → 可能 UI 检查时机问题（在 `argo-tls-debug.log` 写入之前就调了），或 UI 文案条件错。**查 JS 调用链**

**情况 4**：skyline 启动根本没跑新代码 → 用户跑的不是 `just dev-tauri-skyline` 编译出来的新 binary，可能是 release 包 / 老缓存的 binary。**不修代码**，报告

### F. 应用修复（仅在情况 1/3 需要）

如果情况 1：修 `lib.rs` 的 `tls_has_root_cert` 命令实现：
- 改成调 `argo_tls.rs::client_dir()` + 检查 ca.crt 文件存在
- 或改成调 `argo_tls.rs::client_ca_cert_pem(None)`（W10 修复过的函数）
- 加 `tls_log` 记录检查结果

如果情况 3：修 JS 调用链 — 但 JS 在 write-set 之外，**ESCALATE** 而非修。

修完跑 `cargo check -p SkylineStudio --manifest-path apps/skyline/src-tauri/Cargo.toml` 验证编译通过。

### G. 同步到 windev2

如果修了 `lib.rs`，scp 到 windev2：
```bash
scp apps/skyline/src-tauri/src/lib.rs windows_dev_2:D:/code/dang/robot-app-platform/apps/skyline/src-tauri/src/lib.rs
```

验证 windev2 上的 lib.rs 改动到位（grep 关键改动行）。

## Output contract (Chinese, <600 words)

### 1. 诊断结果

情况 1/2/3/4 哪一个？引用具体证据（进程状态 + log 内容 + 代码片段）

### 2. windev2 skyline 进程状态

PID + StartTime + Path

### 3. argo-tls-debug.log 最新条目（skyline 启动后）

tail 20 行 quote

### 4. `tls_has_root_cert` 命令实现 quote

lib.rs 中该命令的完整函数体 + 行号

### 5. 警告文案 quote

前端 i18n catalog 或 component 中"本机缺 rootCA 证书"原文 + 行号

### 6. 修复内容（如适用）

- 修了哪个文件 + 哪些行 + diff 片段
- cargo check 结果
- scp 同步验证

### 7. ESCALATEs

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
