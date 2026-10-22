# PROMPT-W2 — windev2 demoapp latest log + 110.65:50053 fail re-check worker (kimi-k3, read-only)

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
  permission_mode: bypassPermissions   # orchestrator chose to bypass the Bash(ssh:*) approval gate — worker prompt constrains write-set to empty (read-only), no destructive action permitted by prompt
```

---

You are **W2 of windev2 demoapp latest log + 110.65:50053 fail re-check** — a one-shot, read-only worker. The orchestrator already ran W1 (report at `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log`) and confirmed:
- windev2 → `192.168.110.65:50053` is reachable (Test-NetConnection True, SslStream handshake TLS_OK at OS level)
- windev2 → `192.168.100.100:50053` is NOT reachable (TCP refused)
- `~/.argo-tls/` certs all present + valid (ca.crt SHA1 `2C7A91D4...`, client.crt valid 2026-08-14→2027-08-14, client.key exists; all refreshed 16:05:29)
- Tauri process at 16:50:35 = `D:\code\dang\robot-app-platform\target\debug\SudoRobot.exe` (debug build)
- `argo_tls.rs` has zero tracing — current debug process never wrote to `taskflow-debug.log` or `demo-tts-debug.log` (both mtime 16:32)
- W1's `robot-config.json` snapshot: `{"robot_ip":"192.168.100.100:50051", "message":"TLS 连接失败", ...}`

User has now retried with `192.168.110.65:50053` and it ALSO fails with "TLS handshake failed". This rules out "wrong IP / unreachable network" as the sole cause. W2 narrows further.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract is delivered. DO NOT return a plan, outline, or status update. Work continuously until every check is done and the final-message shape is delivered. If you hit an unrecoverable wall (>5 min on one check), record an ESCALATE for that check and move to the next.

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/SPEC-2.md` — this task's spec.
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log` — W1's report (carry-over context; don't redo W1's checks unless re-running them gives NEW signal).
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules.

## Environment

- windev2 SSH: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'` (HostName 192.168.110.217, User jack, key-only). For quote-nest pain, base64-encode the PS script.
- SP000065 SSH: `ssh niic_26 '...'` (192.168.100.100, key-only — but you'll likely reach via 110.65 since niic_26 HostName is 100.100 and W1 said 100.100 is unreachable from windev2... but the workstation THIS worker runs on is a Linux box, not windev2, so 100.100 may be reachable from here. Try niic_26 first; if it fails, try `ssh niic_26@192.168.110.65` or whatever the convention is for the 110.65 path. The SP000065 memory says SSH alias `niic_26` works, so try that first.)
- Linux workstation this worker runs on CAN reach SP000065 via SSH (prior sessions did it).
- SP000065 = **robot host — READ-ONLY, no sudo writes**. If you absolutely must sudo for a read (you shouldn't), use `echo '#sudoai888' | sudo -S cmd` (per memory `Robot Fleet Credentials` — SP000065 still uses old password despite fleet update). Password only in shell, NEVER write it in any file/report/handoffs.
- 3-min no-response = ESCALATE + move on.

## Checks (do all; parallel where independent)

### A. windev2 Tauri process current state
```
Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*SudoRobot*' } | Select-Object ProcessId, Name, ProcessStartTime, CommandLine, ExecutablePath | Format-List
Get-Process | Where-Object { $_.ProcessName -like '*SudoRobot*' } | Select-Object Id, ProcessName, Path, StartTime | Format-List
```
Goal: is PID same as W1's 28188, still running since 16:50:35? Or restarted?

### B. windev2 Tauri app-data dir latest mtime
```
Get-ChildItem 'C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\' -File | Select-Object Name, Length, LastWriteTime | Sort-Object LastWriteTime -Descending | Format-Table -Auto
```
Compare each file's mtime to W1's baseline (16:32:35/16:32:46 for the logs, 16:51:45 for robot-config.json). For any file with mtime > 16:50:35 (process start), tail 100 lines and quote anything matching: `TLS|tls|handshake|cert|50053|110\.65|100\.100|rustls|mTLS|error|ERROR|panic|reqwest|AppError|RequestFailed`.

### C. windev2 `robot-config.json` latest content (VERBATIM)
```
Get-Content 'C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\robot-config.json' -Raw
```
Quote the entire JSON. Note any field changes since W1's snapshot (`robot_ip`, `status`, `message`, etc.).

### D. windev2 → SP000065 fresh re-test (both endpoints)
```powershell
# TCP test, both IPs
Test-NetConnection -ComputerName 192.168.110.65 -Port 50053 -InformationLevel Detailed
Test-NetConnection -ComputerName 192.168.100.100 -Port 50053 -InformationLevel Detailed
# TLS handshake test against 110.65:50053 (the reachable one)
$ErrorActionPreference = 'Continue'
$target = '192.168.110.65'
$port = 50053
$cb = [Net.Security.RemoteCertificateValidationCallback]{ $true }
try {
  $tcp = New-Object Net.Sockets.TcpClient($target, $port)
  $ss = New-Object Net.Security.SslStream($tcp.GetStream(), $false, $cb)
  $ss.AuthenticateAsClient($target)
  $cert = $ss.RemoteCertificate
  Write-Output "TLS_OK subject=$($cert.Subject) issuer=$($cert.Issuer) thumb=$($cert.Thumbprint)"
  $ss.Close(); $tcp.Close()
} catch {
  Write-Output "TLS_FAIL: $($_.Exception.Message)"
  Write-Output "InnerException: $($_.Exception.InnerException.Message)"
}
```
Base64-encode the PS for SSH if quote-nesting breaks. Report exact output — if TLS_OK is still working, then the bug is in the Tauri app, not the OS-level cert chain. If TLS_FAIL, what's the message?

### E. SP000065 server log latest entries (THE smoking gun)
```bash
# Try journalctl first (might be the live log)
ssh niic_26 'journalctl -u argogateway-server --since "30 min ago" --no-pager 2>&1 | tail -200'
# Also tail the file-based log
ssh niic_26 'tail -200 /var/log/robot/argogateway-server/argogateway-server.log 2>&1'
# And grep for recent windev2 IP
ssh niic_26 'grep -E "192\.168\.110\.217|windev2|192\.168\.110\.65|192\.168\.100\.100" /var/log/robot/argogateway-server/argogateway-server.log 2>&1 | tail -50'
```
Look for any entries after 16:40 China time (08:40 UTC). If new entries exist, quote them. Specifically look for: `rustls`, `TLS`, `ClientHello`, `handshake`, `mTLS`, `client cert`, `verify`, `peer`, `Incompatible`, `alert`, `192.168.110.217` (windev2 IP), `192.168.110.65` (the IP windev2 connected from), `connection`, `accept`.

If server log has NEW entries after W1's check, the connection IS reaching the server — the failure is server-side rejection (cert verification, handshake protocol mismatch, etc.).

If server log has NO new entries, the connection is NOT reaching the server — the failure is client-side before TCP connect (panic, config error, URL parse error, etc.).

### F. SP000065 server-side TLS state
```bash
ssh niic_26 'ls -la /etc/argo-tls/'
ssh niic_26 'openssl x509 -in /etc/argo-tls/node.crt -noout -subject -issuer -dates -fingerprint -sha1 2>&1'
ssh niic_26 'openssl x509 -in /etc/argo-tls/ca.crt -noout -subject -issuer -fingerprint -sha1 2>&1'  # might be named ca.crt, client-ca.crt, or similar — adjust
ssh niic_26 'systemctl status argogateway-server --no-pager 2>&1 | head -30'
```
Goal: confirm the server's CA bundle (the CA it uses to verify client certs) has SHA1 matching windev2's ca.crt SHA1 (`2C7A91D418362FF48235381150B470592CB038A0`). If they DON'T match, the server doesn't trust the client cert's CA — that's the bug.

### G. windev2 URL resolution sanity
Read `D:\code\dang\robot-app-platform\apps\demo\src\services\robot-sdk.ts` lines 80-100 to confirm the URL builder logic:
```powershell
Get-Content 'D:\code\dang\robot-app-platform\apps\demo\src\services\robot-sdk.ts' | Select-Object -Skip 80 -First 20
```
Trace what `resolveGatewayBaseUrlFromRobotIp` does with the user's `robot_ip` string. Does it produce `https://192.168.110.65:50053/`? Or something else?

Also check `apps\demo\src\lib\gateway\connect.ts` if it exists (or whatever `getDemoFrontendClient` lives in) — the URL might get further transformed there:
```powershell
Get-ChildItem 'D:\code\dang\robot-app-platform\apps\demo\src\lib\gateway\' -ErrorAction SilentlyContinue
```

### H. Other findings
- `Get-ChildItem $env:TEMP -Filter *argo* -ErrorAction SilentlyContinue` — any TLS-related temp files?
- `Get-ChildItem $env:TEMP -Filter *SudoRobot* -ErrorAction SilentlyContinue` — recent SudoRobot temp
- `$env:RUST_LOG; $env:ARGO_TLS_CLIENT_DIR; $env:ARGO_MTLS_PORT; $env:ARGO_GATEWAY_HOSTS` — env vars set?
- Recent file activity in `D:\code\dang\robot-app-platform\apps\demo\src-tauri\` — any uncommitted source changes? (Just `git status --short` if it's a git repo; if not, skip.)

## Output contract (Chinese, <600 words)

Sections 1–9 per SPEC-2.md §Output contract. End with `Elapsed: <m>min<s>s`.

Quote actual log lines / JSON / fingerprints verbatim. Don't paraphrase.

## Don't

- Don't write any file on windev2 or SP000065.
- Don't sudo on SP000065 unless absolutely necessary for a read — and if you must, use `echo '#sudoai888' | sudo -S cmd` (password only in shell, NEVER in any report/handoffs file).
- Don't restart services. Don't kill processes.
- Don't git push. Don't run destructive git commands.
- Don't add `--no-verify` flags.
- Don't ask the user any questions — judgment calls → ESCALATE in final message.
