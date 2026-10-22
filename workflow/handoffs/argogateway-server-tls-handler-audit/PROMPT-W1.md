# PROMPT-W1 — Audit gateway server `PushZenohRouterConfig` handler

## Worker preamble (prepend to task prompt when dispatching)

```text
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's four questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
5. Code you write that participates in a cross-boundary integration test
   MUST follow the Integration Traceability Contract at
   /home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md
   (read it before writing any logging call). This task writes NO code, so
   the contract is not directly triggered; you do not need to emit events.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger. (This task has no state.md.)
```

## Who
You are the **W1 audit worker** for the Gawain task
`argogateway-server-tls-handler-audit`. You do code reading and risk
analysis only. You do not edit any source code. You produce one markdown
report.

## What
Read the SPEC in full first:
`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-server-tls-handler-audit/SPEC.md`

Then execute the audit. Concretely:

1. **Find the gateway server source code.** Search these locations in
   order:
   - `/home/wangdang/work/ai-stack/` — look for `crates/argogateway`,
     `apps/gateway-server`, or similar
   - `/home/wangdang/work/ai-stack-monitor/` — per user memory, service
     code lives here
   - `/home/wangdang/work/agent_muti/` — per user memory, `ArgoDDS/` lives
     here
   - Grep for `PushZenohRouterConfig`, `push_zenoh_router_config`,
     `pushZenohRouterConfig`, `FrontendRobotControl`, `argogateway` across
     these trees.
   - Also check the deploy script
     `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
     for hints about where the server binary is built / installed from.

2. **Find the `PushZenohRouterConfig` handler.** The RPC is declared in
   `robot_control.proto` (TS port at
   `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts`).
   Find the server-side implementation of this RPC.

3. **Read the handler end-to-end.** What does it do with the received
   `config_json5` string?
   - Parse it? With what parser / struct?
   - Write it to disk? Where?
   - Derive env-file deltas? (Option A check)
   - Restart any services?
   - Read the `metadata` field? Does it look at `tls_mode`?

4. **Check the parser for `deny_unknown_fields`.** This is the E1 risk.
   The frontend now emits a new top-level `transport` field in the
   zenohd-global config when TLS is on. If the server's parser struct has
   `#[serde(deny_unknown_fields)]`, TLS-mode pushes will fail server-side.
   Find the struct, read its serde attributes, give a definitive verdict.

5. **Check for env-file translation.** Does the server, anywhere, translate
   a `transport.link.tls` block (or any TLS signal in the received config)
   into writes to `/etc/argo-gateway/env`? This is the Option A check.
   Search for code that writes to `/etc/argo-gateway/env`,
   `GATEWAY_TLS_ENABLE`, `GATEWAY_TLS_PORT`, etc.

6. **Check for other config-handling code paths.** Systemd generators,
   postinst scripts, watchers, anything that re-derives env from config.

7. **Write the report** with the 10 sections defined in the SPEC.

## Why
The prior frontend implementation (D1+D2 in `robot-app-platform`) emits a
new `transport.link.tls` block in the zenohd-global config when the user
enables TLS. Two risks were ESCALATE'd:

- E1 (highest): if the server rejects unknown fields, TLS-mode pushes
  fail.
- Option A: if the server doesn't translate the block into env-file
  deltas, the frontend change alone is half-broken — TLS config is
  written to disk but the gateway's own env still says plaintext.

The user chose to de-risk both before proceeding. Your report tells the
user whether the frontend change is sufficient, whether server-side
changes are needed, and if so, exactly what.

## Constraints
- **Read-only on all source code.** No `Edit`, no `Write` to source files.
- **Write-set = exactly one file:**
  `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-server-tls-handler-audit/W1-REPORT.md`
- No `git` operations. No network. No full builds.
- You MAY run `cargo check --offline` on a single file if needed to verify
  a struct's serde attributes — but do NOT run full workspace builds.
- You MAY run `grep`, `find`, `rg`, `ls`, `cat` for source discovery.
- If you cannot find the server source after exhaustive search, record an
  ESCALATE with the search commands you ran and the trees you checked. Do
  not fabricate a location.

## Inputs
- SPEC: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-server-tls-handler-audit/SPEC.md`
- Prior audit: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/W1-REPORT.md`
- Prior impl REPORT: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-impl/REPORT.md`
- Deploy script (hints): `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
- Env defaults (hints): `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/env.sh`
- Proto schema (TS port): `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts`
- Search roots (in priority order):
  1. `/home/wangdang/work/ai-stack/`
  2. `/home/wangdang/work/ai-stack-monitor/`
  3. `/home/wangdang/work/agent_muti/`

## Output contract — W1 final message to orchestrator (≤200 words)
Return:
- One-line E1 verdict: `SAFE` / `UNSAFE` / `UNKNOWN`
- One-line Option A verdict: `ALREADY-IMPLEMENTED` / `PARTIAL` / `NOT-IMPLEMENTED` / `UNKNOWN`
- Server source location (path)
- Handler file:line
- One-line risk summary: is the frontend change safe to deploy as-is?
- Path to W1-REPORT.md
- Any ESCALATEs (one line each)
- Elapsed time

Do NOT paste the report content into the message — the orchestrator will
dispatch V1 to read the file and verify. Keep the final message under 200
words.

## Verification
A verifier worker (V1) will be dispatched after you. V1's mandate is to
**disprove** your claims:
- V1 will re-run the source-discovery search to confirm your server
  location is correct (and the only candidate).
- V1 will re-open the handler file and check every `file:line` you cite.
- V1 will read the parser struct's serde attributes directly to verify
  your E1 verdict.
- V1 will grep for env-write code near the handler to verify your Option A
  verdict.
- V1 will look for OTHER config-handling paths you might have missed
  (systemd generators, postinst scripts, watchers).

Any fabricated `file:line`, any E1 or Option A verdict that the actual
code contradicts — V1 returns FAIL and the orchestrator will re-dispatch
you. Cite carefully.

Begin. Read bootstrap.md first, then SPEC, then PROMPT-W1, then prior
audit + impl REPORTs for context, then start searching for the server
source.
