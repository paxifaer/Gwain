# PROMPT-W4 — 实施 W3 P0 方案：客户端 TLS log + JS String(error) bug 修复 (kimi-k3, code edit, no tests)

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
  permission_mode: bypassPermissions   # orchestrator chose to bypass the Bash(cargo check / Write / Edit) approval gates — worker prompt constrains write-set to the 5 declared files, no destructive action permitted by prompt
```

---

You are **W4 of windev2 demoapp log/tracing implementation** — a one-shot, **code-edit** worker. W3 已完成代码审查（报告 `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log`），确认客户端 `argo_tls.rs` 0 tracing + JS 侧 5 处 `String(error)` bug + `AppError` 无 cause 字段。用户已确认 "加快进度,尽量少测试,我这边来测试" — W4 只改代码，不跑测试，用户自己 `just dev` 测。

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract (SPEC-4.md §Output contract) is delivered. DO NOT return a plan, outline, or status update. Work continuously through every P0 item until done. If you hit an unrecoverable wall (>5 min on one file), record an ESCALATE for that file and move to the next.

## Normative reads

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/SPEC-4.md` — this task's spec (single source of truth).
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log` — W3 audit report (carries decision-point list and recommendations).
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules.

## Environment

- All paths in SPEC-4.md §Inputs.
- No SSH. Pure local file edit.
- 3-min no-response on a file = ESCALATE + move on.

## Write-set (strictly bounded)

**Modify only these 5 files**:
1. `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs`
2. `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/error.rs`
3. `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/lib/transport.ts`
4. `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/services/robot-sdk.ts`
5. `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/routes/manage-robot.tsx`

**Optionally create 1 new file**:
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/lib/extract-error.ts` (if you prefer a dedicated helper file over inlining in `transport.ts`)

**Do NOT touch**:
- `Cargo.toml` (no new crate deps)
- `lib.rs` (no new Tauri command — `tls_log` writes directly to file)
- `tauri-app-log` crate
- Any server-side code under `/home/wangdang/work/ai-stack/code/ArgoGateway/`
- Test files (`*.test.ts`, `*_test.rs`, `tests/`) — unless existing tests break due to `cause` field

## Steps (in order; skip cargo check unless time permits)

### Step 1: Read W3 report + current code state

1. Read `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log` — carry W3's decision-point list.
2. Read `argo_tls.rs` (1179 lines) — find current `client_ca_cert_pem` (line 115-123) to see how `~/.argo-tls/` path is resolved. Reuse that path logic in your `tls_log`.
3. Read `error.rs` (103 lines) — see current `AppError` definition.
4. Read the 3 JS files at the relevant lines (transport.ts:300-365, robot-sdk.ts:130-140, manage-robot.tsx:260-270 / 385-395 / 515-530 / 645-655).

### Step 2: Implement `tls_log` in `argo_tls.rs`

At the top of `argo_tls.rs` (after `use` statements, before first function), add:

```rust
/// Write a TLS debug log line to `~/.argo-tls/argo-tls-debug.log`.
/// Best-effort: never panics on IO error. No new crate deps.
fn tls_log(msg: impl AsRef<str>) {
    use std::io::Write;
    use std::time::{SystemTime, UNIX_EPOCH};
    let home = std::env::var_os("USERPROFILE")
        .or_else(|| std::env::var_os("HOME"))
        .and_then(|h| std::path::PathBuf::from(h).into());
    let Some(home) = home else { return };
    let path = home.join(".argo-tls").join("argo-tls-debug.log");
    let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) else { return };
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    let _ = writeln!(f, "[t={}] {}", ts, msg.as_ref());
}
```

If `argo_tls.rs` already has a `home_dir()` helper or `~/.argo-tls/` path resolver (check `client_ca_cert_pem` line 115-123), reuse it instead of inlining env var lookup.

### Step 3: Add `tls_log` calls at all decision points in `argo_tls.rs`

Per W3's decision-point list (SPEC-4 §P0.1), add `tls_log` calls:
- `root_cert_resource_path` (line 20-29) — log each candidate tried + which hit
- `load_client_identity` (line 80-97) — log PEM parse fail, empty certs, key parse fail
- `client_identity_pem` (line 102-108) — log read fail
- `client_ca_cert_pem` (line 115-123) — log which path hit/miss, byte count
- `apply_mtls` (line 142-168) — log at each of 4 AppError exits with step name + err Debug
- `build_http_client` (line 180-185) — log before `builder.build()`, log fail
- `parse_allowed_gateway_url` (line 278-291) — log 3 reject branches, log success
- `gateway_mtls_proxy` (line 300-346) — log line 304 build_http_client entry, log line 317-320 reqwest send fail
- `forward_mtls_stream` (line 383-459) — log line 391, line 407 send fail
- `gateway_mtls_proxy_stream` (line 472-495) — log line 477 reject, line 484 spawn fail

Example pattern:
```rust
// Before
return Err(AppError::request_failed(format!("CA cert load failed: {e}")));
// After
let msg = format!("CA cert load failed: {e}");
tls_log(format!("apply_mtls step=ca_load err={:?}", e));
return Err(AppError::request_failed_with_cause(msg, format!("{:?}", e)));
```

### Step 4: Modify `error.rs` — add `cause: Option<String>`

Change `RequestFailed` variant:
```rust
RequestFailed {
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    cause: Option<String>,
},
```

If there's a `request_failed(s: impl Into<String>) -> Self` helper, add a companion:
```rust
pub fn request_failed_with_cause(s: impl Into<String>, cause: impl Into<String>) -> Self {
    Self::RequestFailed {
        message: s.into(),
        cause: Some(cause.into()),
    }
}
```

Keep existing `request_failed` helper but make it produce `cause: None`.

### Step 5: Update `argo_tls.rs` AppError call sites to use `request_failed_with_cause`

For the 4 AppError exits in `apply_mtls` (line 151/156/158/163 per W3 report) and any other `AppError::request_failed(format!("...{e}"))` in the TLS path, switch to `request_failed_with_cause(format!("..."), format!("{:?}", e))`.

### Step 6: Add `extractInvokeErrorMessage` helper

Either inline in `transport.ts` (top of file, after imports) OR create new `packages/gateway-client/src/lib/extract-error.ts`:

```typescript
export function extractInvokeErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object") {
    const obj = error as { message?: unknown; name?: unknown };
    if (typeof obj.message === "string" && obj.message.length > 0) return obj.message;
    if (typeof obj.name === "string" && obj.name.length > 0) return `${obj.name}: ${JSON.stringify(error)}`;
    return JSON.stringify(error);
  }
  return String(error);
}
```

If inline in `transport.ts`, `export` it so `robot-sdk.ts` and `manage-robot.tsx` can import. If new file, also `export` from package barrel (e.g. `packages/gateway-client/src/lib/index.ts` if exists, or import directly from `./extract-error`).

### Step 7: Fix 5 JS `String(error)` bug sites

- `transport.ts` line 302 — `new Error(String(err))` → `new Error(extractInvokeErrorMessage(err))`
- `transport.ts` line 362 — wrap `invoke<MtlsProxyResponse>("gateway_mtls_proxy", ...)` in try/catch; catch → throw new Error(extractInvokeErrorMessage(e))
- `robot-sdk.ts` line 136 — `error instanceof Error ? error.message : String(error)` → `extractInvokeErrorMessage(error)`
- `manage-robot.tsx` lines 267, 391, 523, 652 — same pattern replacement

### Step 8: Verify with `cargo check` (optional)

Run `cargo check -p SudoRobot --manifest-path /home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/Cargo.toml` once at the end. If it takes >2 min, ESCALATE and skip. Do NOT run `cargo build`/`test`/`clippy`.

If `cargo check` finds errors, fix them and re-run (within the 2-min budget).

### Step 9: Write final report

Follow SPEC-4 §Output contract. Report every changed file + line numbers + key diff snippets. List all ESCALATEs.

## Output contract (Chinese, <800 words)

Per SPEC-4 §Output contract (9 sections). End with `Elapsed: <m>min<s>s`.

Quote actual code lines verbatim (with line numbers). Don't paraphrase.

## Don't

- Don't write files outside the declared write-set.
- Don't run `cargo build`/`test`/`clippy` — user will `just dev` themselves.
- Don't run `just dev`/`just build`.
- Don't run `bun test`/`npm test`.
- Don't modify `Cargo.toml` (no new deps).
- Don't modify `lib.rs` (no new Tauri command).
- Don't modify server-side code.
- Don't modify test files (unless `cause` field breaks existing tests — if so, fix the test minimally and ESCALATE).
- Don't git commit/push.
- Don't add `--no-verify` flags.
- Don't ask the user any questions — judgment calls → ESCALATE in final message.
- Don't add tracing crate dep.
- Don't add chrono crate dep.
- Don't add dirs crate dep.
