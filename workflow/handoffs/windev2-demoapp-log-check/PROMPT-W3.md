# PROMPT-W3 — demo app + argogateway-server log/tracing 充足性审查 worker (kimi-k3, read-only)

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
  reason: code_review
  permission_mode: bypassPermissions   # read-only code review — worker prompt constrains write-set to empty (read-only), no destructive action permitted by prompt
```

---

You are **W3 of windev2 demoapp log/tracing sufficiency review** — a one-shot, **read-only code review** worker. The orchestrator (in another session) has dispatched W1 (windev2 runtime log inspection — done, report at `handoffs/windev2-demoapp-log-check/out-W1.log`) and W2 (windev2 latest log + 110.65:50053 fail re-check — running). User now asks: "派人你看看代码里面的 log 是不是还不够完善,是不是需要加一些" — review whether existing log/tracing in the codebase is sufficient and recommend what to add.

**Your write-set is EMPTY.** Do not create or modify any file. Do not run git operations beyond HEAD-guard. Do not SSH to windev2 or SP000065. Pure code reading + recommendation.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract (SPEC-3.md §Output contract) is delivered. DO NOT return a plan, outline, or status update. Work continuously through every file in the audit list until done. If you hit an unrecoverable wall (>5 min on one file), record an ESCALATE for that file and move to the next.

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/SPEC-3.md` — this task's spec.
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log` — W1's report (carry-over context; tells you what runtime state looks like without tracing).
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules.

## Environment

- No SSH. Pure local file read.
- All code paths in SPEC-3.md §Inputs.
- 3-min no-response on a file = ESCALATE + move on.

## Checks (do all; parallel where independent — multiple Read calls in one message is fine)

### A. 客户端 Rust 侧 — `argo_tls.rs`

Path: `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs`

Read the whole file. For each function below, report:
- Function name + line range
- Current log statements (count + snippet)
- Key decision points (where it can fail silently)
- Recommended tracing calls (specific text)

Functions:
- `apply_mtls` (~line 142)
- `build_http_client` (~line 180)
- `client_ca_cert_pem` (~line 115)
- `gateway_mtls_proxy` (~line 300)
- `gateway_mtls_proxy_stream` (~line 472)
- `forward_mtls_stream` (~line 383)
- `parse_allowed_gateway_url` (search for it; may be elsewhere)
- Any other TLS-related function

For each recommended tracing call, give the exact insertion point (line number + before/after which statement) and exact text, e.g.:
```
tracing::info!(target: "argo_tls", "loading CA from {}", dir.display());
```
or:
```
eprintln!("[argo_tls] CA loaded sha1={}", cert_thumbprint);
```

### B. 客户端 Rust 侧 — `error.rs` + `lib.rs`

Paths:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/error.rs`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/lib.rs`

For `error.rs`:
- Quote the AppError serde representation (`#[serde(tag = "...")]` line + struct/enum definition)
- Confirm: when Tauri invoke rejects with `AppError::RequestFailed("TLS handshake failed")`, what JSON does JS see? Does it include the underlying error chain?
- Recommend: should `AppError` carry a `cause` field or debug string of the underlying error?

For `lib.rs`:
- List every `eprintln!` / `println!` / `tracing::` / `log::` call
- List every `DOUBAO_DEBUG` / `RUST_LOG` env var check
- Confirm where `rustls::crypto::ring::default_provider().install_default()` is called (~line 1341)
- List every `#[tauri::command]` related to logging (`taskflow_debug_log` etc.) and quote their bodies
- Recommend: should there be a `tls_debug_log` Tauri command for `argo_tls.rs` to write to app_data_dir?

### C. 客户端 Rust 侧 — Cargo.toml + windows_subsystem

Path: `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/Cargo.toml`

Quote:
- The `rustls` dependency line
- The `reqwest` dependency line (note feature flags)
- The `tauri-app-log` dependency line
- The `tracing` / `tracing-subscriber` / `log` / `env_logger` dependency lines (or NOT FOUND)
- The `[profile.release]` section (look for `windows_subsystem = "windows"` or in `tauri-build` config)

Also check:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/tauri.conf.json` for any Windows subsystem config
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/build.rs` if exists

Key question: **In release build with `windows_subsystem = "windows"`, does `eprintln!` go anywhere visible?** If NO, recommend that all TLS debug logging must go through `append_app_data_log_line_with_limit` (file-based) rather than `eprintln!`.

### D. 既有日志基建 — `tauri-app-log` crate

Path: `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/crates/tauri-app-log/src/lib.rs`

Read the whole file (likely <500 lines). Report:
- Public API signatures (`append_app_data_log_line`, `append_app_data_log_line_with_limit`)
- Where it writes (app_data_dir + relative_path — quote the path join logic)
- File rotation / size limit logic
- How `argo_tls.rs` could call it (would need `AppHandle` passed down — list call sites that would need plumbing changes)

### E. 客户端 JS 侧 — `String(error)` bug 审查

Paths (read each):
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/lib/transport.ts`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/services/robot-sdk.ts`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/routes/manage-robot.tsx`
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/TlsFailDialog.tsx`

For each file, grep for:
- `String(error)` / `String(err)`
- `error.message` / `err.message`
- `error instanceof Error`
- `JSON.stringify(error)`
- `invoke<MtlsProxyResponse>` and surrounding try/catch

Quote each occurrence with line number and surrounding 3 lines of context.

For each `String(error)` bug, recommend the fix:
```typescript
// Before
const message = error instanceof Error ? error.message : String(error);
// After
const message = error instanceof Error
  ? error.message
  : (error?.message ?? JSON.stringify(error));
```
Or specifically for Tauri invoke rejections (which return `{name, message}` plain objects):
```typescript
const message = error?.message ?? (typeof error === 'object' ? JSON.stringify(error) : String(error));
```

### F. 服务端 Rust 侧 — `argo-gateway-server` TLS accept 路径

Root: `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/`

First, list the directory tree (no deeper than 2 levels):
```bash
find /home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/ -maxdepth 2 -type f -name "*.rs" | sort
```

Read these files (or report NOT FOUND):
- `src/main.rs` — look for: TLS listener setup, accept loop, rustls ServerConfig builder, CryptoProvider install (~line 135 per prior session note), any tracing/log calls
- `src/connect.rs` or similar (search for `accept`, `TlsAcceptor`, `ServerConfig`)
- `src/direct_service.rs` or similar (mTLS direct service)
- `Cargo.toml` — check for `tracing`, `tracing-subscriber`, `env_logger`, `log` deps; check for `rustls` features (`logging`?)

For each file, report:
- TLS-related functions + line ranges
- Current log statements (count + snippet)
- Key decision points where TLS handshake / cert verify can fail silently
- rustls 0.23 server-side: is there a custom `rustls::server::Verifier`? Is there a `rustls::LoggingSide`? (rustls 0.23 has `crypto::CryptoProvider::default()` + Logger via `rustls::log::LogSink` trait — search for it)
- Is `RUST_LOG` env var read at startup?

Recommend: where to add `tracing::info!` / `tracing::error!` calls in server-side TLS accept path. Specifically:
- On every new TCP accept: log peer IP
- On every TLS handshake start: log peer IP + SNI
- On every cert verify fail: log client cert subject + reason
- On every handshake success: log negotiated cipher + ALPN

### G. W1/W2 cross-reference

Read W1's report: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log`

Note what W1 found that would have been visible IF tracing existed:
- W1 had to infer cert state from file hashes instead of from log
- W1 had to test TCP/TLS reachability externally instead of from log
- W1 found `argo_tls.rs` has "zero tracing" — confirm this from your own read

If W2 has completed by the time you reach this check (check `out-W2.log` size > 0), also note W2's findings.

## Output contract (Chinese, <800 words)

Sections 1–6 per SPEC-3.md §Output contract. End with `Elapsed: <m>min<s>s`.

Quote actual code lines verbatim (with line numbers). Don't paraphrase code.

For each recommendation, give:
- File path + line number
- Insertion point (before/after which line)
- Exact recommended code (tracing call text or JS fix snippet)

## Don't

- Don't write any file (write-set is EMPTY).
- Don't SSH to any host.
- Don't run git operations beyond HEAD-guard.
- Don't modify Cargo.toml.
- Don't ask the user any questions — judgment calls → ESCALATE in final message.
- Don't dispatch sub-agents.
- Don't run builds or tests — this is a read-only audit.
