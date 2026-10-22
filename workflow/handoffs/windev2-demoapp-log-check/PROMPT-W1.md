# PROMPT-W1 — windev2 demoapp run-log inspection worker (kimi-k3, read-only)

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

You are **W1 of windev2 demoapp run-log inspection** — a one-shot, read-only worker. The orchestrator (in another session) is debugging why SudoRobot demoapp on windev2 fails TLS handshake to SP000065 (192.168.110.65:50053) even though a raw PowerShell `SslStream.AuthenticateAsClient` from a different win box succeeded against the same endpoint with the same cert chain. The Tauri app's UI shows "TLS handshake failed. Choose to abort or fall back to plaintext." with reason "[object Object]" — the real error is being eaten by a JS bug. The `argo_tls.rs` source has zero tracing today.

Your job: squeeze every signal already on disk out of windev2 (logs, cert files, process state) — **read-only, no modifications, no sudo** — so the orchestrator can decide whether to add tracing + rebuild or pursue another fix.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract below is delivered. DO NOT return a plan, an outline, a status update, or "next I'll ..." announcements. Work continuously until every check is done and the final-message shape is delivered. If you hit an unrecoverable wall (>5 min on one check), record an ESCALATE for that check and move to the next one.

## Normative read

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/SPEC-1.md` — the spec (this task's single source of truth).
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules.

## Environment

- SSH alias: `windows_dev_2` (HostName 192.168.110.217, User jack, key-only).
- SP000065 (robot, 192.168.110.65 / 192.168.100.100, port 50053 mTLS) — **do not modify anything on SP000065**, but you may read-check its cert via `openssl s_client` if useful.
- All SSH must use PowerShell: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`.
- If PowerShell quote-nesting breaks, base64-encode the script:
  ```bash
  PS_B64=$(echo -n 'Get-ChildItem C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\ -Recurse | Select-Object FullName, Length, LastWriteTime' | base64 -w0)
  ssh windows_dev_2 "powershell -NoProfile -Command \"\$cmd = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('$PS_B64')); Invoke-Expression \$cmd\""
  ```
  Prefer direct quotes when feasible; only base64 when nesting fails.
- Single SSH command ≤ 25s. Run independent checks as parallel SSH calls (multiple `&`-backgrounded bash subshells or a single `parallel`-style dispatch — your call).
- 3-minute no-response on a check = log as problem + move to next.

## Checks (do all, in any order that fits parallel SSH)

### A. Running Tauri process
```
Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*SudoRobot*' -or $_.CommandLine -like '*tauri*dev*' -or $_.CommandLine -like '*robot-app-platform*' } | Select-Object ProcessId, Name, ProcessStartTime, CommandLine, ExecutablePath | Format-List
Get-Process | Where-Object { $_.ProcessName -like '*SudoRobot*' -or $_.ProcessName -like '*robot*' } | Select-Object Id, ProcessName, Path, StartTime | Format-List
```
Goal: confirm whether running debug (`target\debug\SudoRobot.exe`) or release (`target\x86_64-pc-windows-msvc\release\SudoRobot.exe` or `D:\code\dang\SudoRobot.exe`), and the StartTime.

### B. Tauri app-data dir listing
```
Get-ChildItem 'C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\' -Recurse -File | Select-Object FullName, Length, LastWriteTime | Sort-Object LastWriteTime -Descending | Format-Table -Auto
```
If the dir doesn't exist, also try `[Environment]::GetFolderPath('ApplicationData')` + `\com.sudo-robot.sudorobot\` and `%LOCALAPPDATA%\com.sudo-robot.sudorobot\`.

### C. Tauri log tail (every `*.log` file found in B)
For each `*.log`:
```
Get-Content -Path <file> -Tail 100 | Select-String -Pattern 'TLS|tls|handshake|cert|50053|110\.65|100\.100|rustls|mTLS|error|ERROR|panic|reqwest' -CaseSensitive:$false
```
Quote matching lines verbatim in the final message. If no matches, say "no TLS-related lines in <file>".

### D. `~/.argo-tls/` directory contents + SHA1 + cert metadata
```
$dir = 'C:\Users\jack\.argo-tls'   # also try $env:USERPROFILE\.argo-tls if HOME is different
Get-ChildItem $dir -File | Select-Object Name, Length, LastWriteTime
Get-FileHash "$dir\ca.crt" -Algorithm SHA1
Get-FileHash "$dir\client.crt" -Algorithm SHA1
$ca = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new("$dir\ca.crt")
$ca | Format-List Subject, Issuer, NotBefore, NotAfter, Thumbprint
$client = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new("$dir\client.crt")
$client | Format-List Subject, Issuer, NotBefore, NotAfter, Thumbprint
```
If `~/.argo-tls/` doesn't exist or is empty, ESCALATE — that's likely the bug (no client cert = `apply_mtls` errors with "mTLS client cert missing").

### E. windev2 → SP000065 reachability
```
Test-NetConnection -ComputerName 192.168.110.65 -Port 50053 -InformationLevel Detailed
Test-NetConnection -ComputerName 192.168.100.100 -Port 50053 -InformationLevel Detailed
```

### F. TLS handshake from windev2 to SP000065:50053 (proves OS-level cert chain works from THIS machine)
```powershell
$ErrorActionPreference = 'Continue'
$target = '192.168.110.65'
$port = 50053
$cb = [Net.Security.RemoteCertificateValidationCallback]{ $true }
try {
  $tcp = New-Object Net.Sockets.TcpClient($target, $port)
  $ss = New-Object Net.Security.SslStream($tcp.GetStream(), $false, $cb)
  $ss.AuthenticateAsClient($target)
  $cert = $ss.RemoteCertificate
  Write-Output "TLS_OK subject=$($cert.Subject) issuer=$($cert.Issuer)"
  $ss.Close(); $tcp.Close()
} catch {
  Write-Output "TLS_FAIL: $($_.Exception.Message)"
}
```
Wrap it as base64 to avoid SSH quote issues. Report `TLS_OK` or `TLS_FAIL: <message>`.
Also run against `192.168.100.100:50053` for comparison.

### G. Other findings
- `git -C D:\code\dang\robot-app-platform status --short && git -C D:\code\dang\robot-app-platform log --oneline -5` — recent repo state
- `Get-ChildItem D:\code\dang\robot-app-platform\ -Filter *.log -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime` — stray log files in the code dir
- `Get-ChildItem $env:TEMP -Filter *SudoRobot* -ErrorAction SilentlyContinue` — leftover temp files
- `Get-ChildItem $env:TEMP -Filter *argo* -ErrorAction SilentlyContinue` — TLS-related temp
- `$env:RUST_LOG; $env:ARGO_TLS_CLIENT_DIR; $env:ARGO_MTLS_PORT; $env:ARGO_GATEWAY_HOSTS` — relevant env vars set?

## Output contract (final message — Chinese, <500 words)

Section order:
1. **Tauri 进程** — PID, Path, StartTime, debug/release verdict
2. **Tauri app-data dir 列表** — files + mtime
3. **Tauri log 末尾摘抄** — quoted matching lines per file, or "no TLS-related lines"
4. **`~/.argo-tls/` 文件清单 + SHA1 + cert metadata** — ca.crt / client.crt / client.key existence, SHA1, Subject/Issuer/NotBefore/NotAfter/Thumbprint for ca.crt and client.crt
5. **windev2 → SP000065 连通性** — Test-NetConnection results for both 110.65 and 100.100; TLS handshake test results for both
6. **其他发现** — git state, stray logs, env vars, anything weird
7. **ESCALATEs** — every check that failed/timed out/required a judgment call, with the exact reason

End with one line: `Elapsed: <m>min<s>s`.

## Don't

- Don't write any file on windev2 or SP000065.
- Don't sudo. Don't restart services. Don't kill processes.
- Don't git push. Don't run destructive git commands.
- Don't `cd` into git repos and run `git checkout`/`reset`/`clean`.
- Don't add `--no-verify` flags.
- Don't ask the user any questions — make judgment calls and record them as ESCALATEs.
