# SPEC-1 — windev2 demoapp run-log inspection (read-only)

## Goal

User runs SudoRobot demoapp (Tauri 2 + React, bundle id `com.sudo-robot.sudorobot`) on **windev2** (SSH alias `windows_dev_2`, HostName 192.168.110.217, User jack, key-only auth). They clicked "TLS connect" to SP000065 (192.168.110.65:50053 mTLS) in the UI; UI shows the static string "TLS handshake failed. Choose to abort or fall back to plaintext." with reason field "[object Object]" — the real TLS error is being swallowed by a JS `String(plainObject)` bug.

This worker's job is **read-only inspection**: pull every relevant log/state file on windev2 that might contain the real TLS error or hint at where the handshake fails, and report findings. Do not modify anything.

## Why

PowerShell TLS handshake from windev2's predecessor (win) to 110.65:50053 succeeded (cert chain valid at OS level), but the Tauri app still fails. The server log on SP000065 shows NO new TLS attempts after 08:40 UTC restart — meaning the client side is failing before/during the handshake without the connection reaching the server, OR the connection reaches but the server doesn't log it. We need to see what the client side actually errors with.

The `argo_tls.rs` source has **zero** tracing today. The JS layer wraps the Tauri invoke rejection (a plain `{name, message}` object from `AppError::RequestFailed`) with `String(error)` → `"[object Object]"`. So no information reaches the UI.

Before adding tracing (which requires a rebuild + relaunch by the user), we should squeeze whatever signal already exists on disk out of windev2:
- Tauri app-data-dir logs (taskflow-debug.log, demo-tts-debug.log, game-debug.log — none are TLS-specific, but might have errored nearby)
- The `~/.argo-tls/` dir (ca.crt, client.crt, client.key) — verify presence + SHA1 + cert chain
- The running process — confirm whether debug or release binary, what path, what start time
- TCP reachability windev2 → 192.168.110.65:50053 + TLS handshake test from windev2 (proves the OS-level cert chain works from THIS machine; previous test was from a different win box)
- Any other log files in the code dir or temp that might have captured stderr

## Inputs

- SSH alias: `windows_dev_2`
- Tauri bundle id: `com.sudo-robot.sudorobot`
- Expected Tauri app-data dir: `C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\`
- Expected client cert dir: `C:\Users\jack\.argo-tls\` (or whatever `HOME` resolves to — check `echo $env:HOME` and `[Environment]::GetFolderPath('UserProfile')`)
- Code dir: `D:\code\dang\robot-app-platform\`
- SP000065 mTLS endpoint: `192.168.110.65:50053` (also reachable at `192.168.100.100:50053`)
- Expected root CA cert: fingerprint SHA1 `2C7A91D4...` (full hash to be confirmed by worker from CA file on windev2)
- Server cert re-signed today (2026-08-18 16:39 UTC+8) with SAN including both 100.100 and 110.65 + DNS:SP000065

## Constraints

- **READ-ONLY**. Do not modify any file on windev2 or SP000065. No sudo. No git push. No service restart. No process kill.
- Single SSH ≤ 25s. Run parallel SSH calls when independent.
- SSH must use PowerShell: `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`. If quote-nesting breaks, base64-encode the PS script.
- 3-minute no-response = log as problem + move to next check.
- Don't write to the SP000065 robot host (it's a robot, only read-check).
- The user is in mainland China — any installs need proxy `http://127.0.0.1:7897`. (Probably irrelevant for this read-only task; no installs expected.)

## Output contract (worker final message — Chinese, <500 words)

Report these sections, in this order:

1. **Tauri 进程** — PID, binary path, debug/release, StartTime, CommandLine (if available)
2. **Tauri app-data dir 列表** — files in `C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\` with size + mtime
3. **Tauri log 末尾摘抄** — for each `*.log` file found, tail 100 lines and quote any line containing: `TLS`, `tls`, `handshake`, `cert`, `50053`, `110.65`, `100.100`, `rustls`, `mTLS`, `error`, `ERROR`, `panic`, `reqwest`. If nothing matches, say so explicitly.
4. **`~/.argo-tls/` 文件清单 + SHA1** — list `ca.crt`, `client.crt`, `client.key` (or whatever's there), with SHA1 fingerprints (Get-FileHash -Algorithm SHA1). For `ca.crt`, also dump issuer/subject via `Get-Content` + `[X509Certificate2]::new($path)` and show Issuer/Subject/NotBefore/NotAfter.
5. **windev2 → SP000065 连通性**
   - `Test-NetConnection 192.168.110.65 -Port 50053` result (TcpTestSucceeded, RemoteAddress)
   - TLS handshake test result: write a small PS snippet that opens `SslStream.AuthenticateAsClient('192.168.110.65', ...)` with `[Net.Security.RemoteCertificateValidationCallback]{ $true }` to bypass cert validation (just to see if the TLS handshake itself completes from windev2), and report Subject + Issuer + any error message.
6. **其他发现** — anything unusual (weird env vars, leftover temp files, browser console, alternative launch scripts, recent git state if `D:\code\dang\robot-app-platform\` is a git repo).
7. **ESCALATEs** — any judgment calls made alone, any checks that timed out or failed, any ambiguities.

End with one line: `Elapsed: <m>min<s>s`.

## Verification

Worker is also the verifier here (one-shot read-only task). The user reads the report and decides next step (add tracing + rebuild, or some other fix based on what the logs show).
