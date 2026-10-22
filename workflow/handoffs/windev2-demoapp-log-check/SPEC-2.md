# SPEC-2 — windev2 demoapp latest log + 110.65:50053 fail re-check (read-only)

## Goal

User just retried TLS connect from windev2 demoapp to SP000065 — this time using `192.168.110.65:50053` (the W1-confirmed reachable IP). UI still shows "TLS handshake failed. Choose to abort or fall back to plaintext." with reason "[object Object]". User asks "派人看看最新的log,192.168.110.65:50053也是报错".

W1 already established (report at `handoffs/windev2-demoapp-log-check/out-W1.log`):
- windev2 → `192.168.110.65:50053` TCP **True** + SslStream handshake **TLS_OK** at the OS level
- windev2 → `192.168.100.100:50053` is **unreachable** (TCP refused)
- `~/.argo-tls/` certs all present + valid (ca.crt, client.crt, client.key refreshed 16:05:29)
- Tauri process at 16:50:35 = `D:\code\dang\robot-app-platform\target\debug\SudoRobot.exe` (debug build)
- `argo_tls.rs` has zero tracing — current debug process never wrote to `taskflow-debug.log` or `demo-tts-debug.log` (both mtime 16:32)
- W1's robot-config.json snapshot: `{"robot_ip":"192.168.100.100:50051", ...}` — that was the 100.100 attempt

Now the user has tried 110.65:50053 and it ALSO failed. This rules out "wrong IP / unreachable network" as the sole cause. Something else is broken — either:
- (a) The Tauri app is failing client-side before TCP connect (config parse, identity build, CA load, etc.)
- (b) The TCP connects but server rejects the handshake (server-side CA bundle missing the client cert's CA, or client cert not signed by the right CA, or client cert expired)
- (c) The user typed something other than `https://192.168.110.65:50053/` and the URL got mangled in the resolve step
- (d) The mTLS handshake completes but reqwest errors at HTTP/2 layer (cert OK but server rejects the gRPC call)

W2's job is to look at **the LATEST state** (logs, robot-config.json, server-side log + cert) and tell the orchestrator which branch it is — without modifying anything.

## Why

W1 narrowed it to "not the network path / not the cert chain (at OS level)". W2 narrows further: is it client-side (Rust panic / reqwest error before TCP) or server-side (server got the TLS ClientHello but rejected it)? The server's log is the smoking gun — if W2 finds new TLS server entries after 16:40 UTC (the 08:40 UTC restart baseline from prior session), it's (b)/(d); if W2 finds none, it's (a)/(c).

## Inputs

- windev2 SSH: `windows_dev_2` (192.168.110.217, jack, key-only)
- SP000065 SSH: `niic_26` (192.168.100.100, key-only) — robot host, **READ-ONLY, no sudo writes**
  - Note: per memory `Robot Fleet Credentials`, fleet password is `Hillbot2Dev` but SP000065 specifically still uses `#sudoai888` for sudo (fleet update didn't propagate to this box). For READ-ONLY checks you should NOT need sudo at all — `journalctl -u argogateway-server` and `cat /etc/argo-tls/*.crt` etc. are all unprivileged.
- windev2 Tauri app-data dir: `C:\Users\jack\AppData\Roaming\com.sudo-robot.sudorobot\`
- windev2 `~/.argo-tls/`: `C:\Users\jack\.argo-tls\`
- SP000065 server cert dir: `/etc/argo-tls/` (server cert + CA bundle)
- SP000065 server log: `/var/log/robot/argogateway-server/argogateway-server.log` AND `journalctl -u argogateway-server` (whichever has newer entries)
- Code dir on windev2: `D:\code\dang\robot-app-platform\`
- W1 baseline: W1 ran at ~17:14 China time. User retried after that.

## Constraints

- **READ-ONLY**. No file modifications. No service restarts. No process kills. No sudo on SP000065 unless absolutely necessary for a read — and if you must, use `echo '#sudoai888' | sudo -S cmd` per memory (password only in shell, never in report).
- Single SSH ≤ 25s. Parallel SSH where independent.
- windev2 SSH: PowerShell only, `ssh windows_dev_2 'powershell -NoProfile -Command "..."'`, base64-encode on quote-nest pain.
- SP000065 SSH: bash, `ssh niic_26 'bash -c "..."'` or just `ssh niic_26 "..."`. ≤25s per call.
- 3-min no-response = ESCALATE + move on.
- Do not fabricate. If a check fails, say so.

## Output contract (Chinese, <600 words)

1. **windev2 Tauri 进程现在状态** — PID, Path, StartTime, still running or restarted since W1?
2. **windev2 Tauri app-data dir 最新 mtime** — list `*.log` files with current mtime. Compare to W1's 16:32 baseline. If any log has new content (mtime > 16:50:35 = process start), quote the new lines.
3. **windev2 `robot-config.json` 最新内容** — quote the JSON verbatim. Note any IP/port/scheme change since W1.
4. **windev2 → SP000065:50053 fresh re-test** — run SslStream.AuthenticateAsClient('192.168.110.65', 50053) with `[Net.Security.RemoteCertificateValidationCallback]{ $true }` (bypass cert validation just to test handshake reachability). Report TLS_OK or TLS_FAIL with exact message. Also Test-NetConnection to 110.65:50053 and 100.100:50053 (sanity check network state didn't change since W1).
5. **SP000065 server log latest entries** — `journalctl -u argogateway-server --since "20 minutes ago"` + `tail -200 /var/log/robot/argogateway-server/argogateway-server.log`. Quote any new entries after 16:40 China time (08:40 UTC). Specifically look for: `rustls`, `TLS`, `ClientHello`, `handshake`, `mTLS`, `client cert`, `verify`, `50053`, `peer`, `Incompatible`, `alert`, `192.168.110.217` (windev2's IP).
6. **SP000065 server-side TLS state**:
   - `ls -la /etc/argo-tls/` — what files are there (server cert, server key, CA bundle)
   - `openssl x509 -in /etc/argo-tls/node.crt -noout -subject -issuer -dates -fingerprint -sha1` — confirm server cert is the one re-signed today
   - `openssl x509 -in /etc/argo-tls/ca.crt -noout -subject -issuer -fingerprint -sha1` (or whatever the CA file is named) — compare SHA1 to windev2's `~/.argo-tls/ca.crt` SHA1 (`2C7A91D418362FF48235381150B470592CB038A0`). They MUST match for the server to trust the client cert.
   - If the server has a separate `client-ca.crt` or similar, also dump its fingerprint.
   - `systemctl status argogateway-server --no-pager` (don't pipe to less) — current service status + last 10 log lines
7. **windev2 端口/SAN sanity**:
   - Does the demo app's `robot_ip` field parse to a URL with `https://` scheme and port 50053? Quote the JSON `robot_ip` and infer what URL `resolveGatewayBaseUrlFromRobotIp` in `apps/demo/src/services/robot-sdk.ts` would produce.
   - Also check `apps/demo/src/services/robot-sdk.ts` lines 81-100 to confirm the URL builder logic — does the user's typed IP/port combo produce the right mTLS URL?
8. **结论** — which branch (a/b/c/d) does the evidence point to? Quote the smoking-gun log line.
9. **ESCALATEs** — every failed check, judgment call, or ambiguous signal.

End with one line: `Elapsed: <m>min<s>s`.

## Verification

W2's report IS the verification — the orchestrator reads it and decides next step. If the report is ambiguous, the orchestrator may dispatch W3 with a more targeted check.
