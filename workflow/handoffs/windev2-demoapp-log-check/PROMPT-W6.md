# PROMPT-W6 — windev2 `argo-tls-debug.log` + 决策点 tracing 检查 (kimi-k3, read-only)

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
  reason: search_and_inspection
  permission_mode: bypassPermissions   # read-only worker — prompt constrains write-set to empty
```

---

You are **W6** — a one-shot, **read-only** worker. W4+W5 已修改代码（W4 加 `tls_log` helper 写到 `~/.argo-tls/argo-tls-debug.log` + 10+ 决策点埋点；W5 修 `client_dir()` 加 `USERPROFILE` 兜底）。用户现在已 `just dev-demo` 测试过 TLS 连接 SP000065。W6 去看 windev2 上的 `argo-tls-debug.log` 实际产出了什么。

**Write-set is EMPTY.** Read-only。

## CRITICAL: NO PARTIAL RETURNS

完成全部检查后按输出契约报告。3-min no-response = ESCALATE + move on。

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W2.log` — W2 报告（根因 §7-8，`client_dir()` bug）
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W4.log` — W4 报告（`tls_log` 决策点埋点清单 §2）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W5.log` — W5 报告（`client_dir()` USERPROFILE 修复）
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Environment

- windev2 SSH：`ssh windows_dev_2 'powershell -NoProfile -Command "..."'`（HostName 192.168.110.217, User jack, key-only）。引号嵌套 pain 就 base64 编码 PS 脚本。
- 单条 SSH ≤25s。3-min no-response = ESCALATE + move on。
- 不修改 windev2 任何文件。

## Checks

### A. windev2 `~/.argo-tls/argo-tls-debug.log` 文件存在性 + 大小 + mtime

```powershell
Get-ChildItem 'C:\Users\jack\.argo-tls\' -Filter *.log -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -Auto
Get-ChildItem 'C:\Users\jack\.argo-tls\' -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -Auto
```

如果 `argo-tls-debug.log` 不存在 → ESCALATE：可能用户还没启动新 build，或 W4/W5 改动没被编译进去。
如果存在 → 报告 size + mtime。mtime 应该是用户最近 `just dev-demo` 测试时间。

### B. `argo-tls-debug.log` 全文逐行 quote

```powershell
Get-Content 'C:\Users\jack\.argo-tls\argo-tls-debug.log' -Raw
```

逐行 quote。预期看到的事件名（来自 W4 §2 决策点埋点清单）：
- `client_dir resolved dir=...` — W5 新加的 line 19
- `root_cert_resource_path ...`
- `load_client_identity ...`
- `client_identity_pem ...`
- `client_ca_cert_pem ...`
- `apply_mtls step=...` — 4 个出口
- `build_http_client ok use_tls=...` / `build_err ...`
- `parse_allowed_gateway_url ...`
- `gateway_mtls_proxy entry method= url= ...` / `send_err ...` / `ok status=...`
- `forward_mtls_stream ...`
- `gateway_mtls_proxy_stream ...`

特别关注：
1. **`client_dir resolved dir=...`** — 是否解析到 `C:\Users\jack\.argo-tls`（W5 修复后应该如此）？还是仍然 `.\.argo-tls` 之类相对路径（修复未生效）？
2. **`apply_mtls step=check_client_identity err=missing`** — 如果还看到这条，说明 cert 仍未找到（W5 修复未生效或新 build 未跑）。
3. **`gateway_mtls_proxy ok status=200`** — 如果看到这条，TLS 连接成功！
4. **`send_err is_connect=... err=...`** — 网络/握手层错误的具体内容。

### C. windev2 Tauri 进程当前状态

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*SudoRobot*' } | Select-Object ProcessId, Name, ProcessStartTime, ExecutablePath | Format-List
```

PID + StartTime + Path。和 W1/W2 比对（W2 看到 PID 28188 StartTime 16:50:35）—— 如果还是 28188，**用户没重启进程**，W4/W5 改动没生效（用户必须 `just dev-demo` 重启加载新代码）。如果新 PID + 新 StartTime，说明用户已经重启。

### D. windev2 robot-config.json 最新内容

```powershell
Get-Content 'C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\robot-config.json' -Raw
```

Quote verbatim。看用户当前 `robot_ip` 是什么。

### E. app-data dir 其他 log 最新 mtime

```powershell
Get-ChildItem 'C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\' -Filter *.log -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Sort-Object LastWriteTime -Descending | Format-Table -Auto
```

看 taskflow-debug.log / demo-tts-debug.log 有没有新内容（W2 时 mtime 锁死 16:32）。

### F. SP000065 服务端 log 最新条目（看 ClientHello 有没有到达）

```bash
ssh niic_26 'journalctl -u argogateway-server --since "30 min ago" --no-pager 2>&1 | tail -100'
ssh niic_26 'tail -100 /var/log/robot/argogateway-server/argogateway-server.log 2>&1'
```

W2 时服务端 16:40 后 0 条 TLS 条目。现在用户测试后服务端有没有新 TLS 接收记录？如果有 → ClientHello 到达了，看握手结果。如果还是 0 → 仍未到达。

## Output contract (Chinese, <600 words)

### 1. `argo-tls-debug.log` 文件状态

存在 / 不存在 + size + mtime + 创建时间推断（用户测试时间）。

### 2. `argo-tls-debug.log` 全文逐行 quote

按时间顺序 quote 每一行。如果 >200 行，只 quote 头 50 + 尾 100，中间说明省略。

### 3. 关键决策点解读

- `client_dir resolved dir=` → 实际解析到什么路径？W5 修复生效了吗？
- 用户这次 TLS 连接走到哪一步：`apply_mtls` 入口 / `check_client_identity` / `ca_from_pem` / `build_http_client` / `gateway_mtls_proxy send` / `ok status=200`？
- 如有错误，错误 message + cause 字段内容是什么？
- W4 加的 `tls_log` 输出有没有完整覆盖所有决策点？有没有缺漏？

### 4. Tauri 进程状态

PID + StartTime + Path。和 W2 的 28188/16:50:35 比对，**用户重启了吗**？

### 5. robot-config.json 当前内容

Verbatim quote。`robot_ip` 是什么？

### 6. SP000065 服务端 log 最新条目

W2 之后有没有新条目？ClientHello 这次到达服务器了吗？

### 7. 结论

W4 tracing + W5 `client_dir()` 修复，在用户实际测试中：
- (a) 完全成功，TLS 连接通了 — 看到 `ok status=200` + 服务端新 accept 条目
- (b) W5 修复生效（`client_dir resolved` 指向 `C:\Users\jack\.argo-tls\`）但 TLS 仍失败 — 看新错误是什么
- (c) W5 修复未生效（仍是 `./argo-tls` 或 SudoRobot.exe CWD 相对路径）— 用户没重启加载新代码
- (d) 用户根本没重新启动 `just dev-demo` — Tauri PID 还是 28188 + `argo-tls-debug.log` 不存在或 mtime 老旧

### 8. ESCALATEs

所有未完成的检查、判断分歧。

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write any file on windev2 or SP000065.
- Don't sudo on SP000065. Don't restart services. Don't kill processes.
- Don't git push or run destructive git commands.
- Don't add `--no-verify` flags.
- Don't ask the user any questions — judgment calls → ESCALATE.
