# V2 Verifier Verdict — Lifecycle Unified API Phase 2b (ArgoGateway read-only)

- **Verifier**: kimi-k3, 30 min hard cap
- **Mandate**: adversarial — prove or disprove D-014 (Scheme A: ArgoGateway needs 0 code change
  for `lifecycle.execute` via the Chat RPC tunnel). Disprove first; only ACCEPT if no
  counterexample found.
- **Scope**: `code/ArgoGateway/**` (read-only audit). Cross-references `code/ArgoWatch/**`
  (Phase 1 byte-exact lock) + `code/frontend/robot-app-platform/**` (Phase 2a, uncommitted)
  for end-to-end tracing only — 0 modifications anywhere.
- **HEAD guards**:
  - ArgoGateway: `da0bb4f2c5de41ce68b699a8abca95447ca75558` on `feat/p9-lifecycle-unified-gateway`
  - ArgoWatch: `d2b3b9db685937313889cace8430fe86c43884a1`
  - robot-app-platform: `f7512bd94b4a9ef3c529407d75b8ed8f4bb14d02` on `feat/p9-lifecycle-unified-frontend`
- **sha256 sentry**: `demo-app-lifecycle/src/runtime/reconcile.rs` =
  `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` ✓

## Verdict: ACCEPT

All 10 adversarial checks PASS. D-014's central claim holds: ArgoGateway's existing generic
`/watch/…/submit` rule at `src/argo-gateway-chat/src/lib.rs:224-226` covers
`lifecycle/execute/submit` uniformly with the 7 legacy lifecycle topics. Zero code change
required.

## Adversarial checks

### V2.1 — `infer_response_topic` matches `lifecycle/execute/submit`
- Finding: **PASS**
- Evidence: `src/argo-gateway-chat/src/lib.rs:217-231`. Four rules in order:
  - R1 (218–220): `ends_with("/task/submit")` → replace with `/task/status`
  - R2 (221–223): `contains("/roboskill/") && ends_with("/submit")` → `/result`
  - R3 (224–226): `contains("/watch/") && ends_with("/submit")` → `/result`
  - R4 (227–229): `ends_with("/agent/chat/submit")` → `/result`
- Trace for actual wire topic. `resolve_topic` at lib.rs:207–215 prefixes `/fleet/bot/`
  before `infer_response_topic` is called via lib.rs:63 (`let topic = resolve_topic(req);`)
  → lib.rs:100. So resolved input is `/demo/robot_1/watch/lifecycle/execute/submit`, not
  the bare `watch/lifecycle/execute/submit`. Either way:
  - R1: `ends_with("/task/submit")` — false (ends with `/execute/submit`), skip.
  - R2: `contains("/roboskill/")` — false, skip.
  - R3: `contains("/watch/")` true ✓, `ends_with("/submit")` true ✓ → returns
    `Some("<prefix>/watch/lifecycle/execute/result")`. Prefix preserved verbatim via
    single-pass `str::replace("/submit", "/result")`.
  - R4 unreachable.
- No earlier rule shadows R3: R1 requires the literal tail `/task/submit`; R2 requires
  `/roboskill/` infix. Neither matches.
- Counterexample found: no.

### V2.2 — `infer_response_topic` is actually called in the Chat RPC path
- Finding: **PASS**
- Evidence:
  - Sole production caller: `src/argo-gateway-chat/src/lib.rs:100`
    (`let Some(resp_topic) = infer_response_topic(&topic) else { … }`), inside
    `ChatExecutor::execute` (lib.rs:52–148). The other two `infer_response_topic` matches
    in the file are unit tests at lib.rs:296 and lib.rs:304.
  - `ChatExecutor` wiring: `src/argo-gateway-server/src/main.rs:174` constructs
    `Arc::new(ChatExecutor::new(Arc::new(sdk.clone())))`, injected into
    `RobotControlServiceImpl` at `src/argo-gateway-server/src/robot_control.rs:75,86,95`.
  - Connect handler: `robot_control.rs:437 async fn chat(&self, Request<ChatRequest>)` →
    converts gateway.v1 → proto ChatRequest at `robot_control.rs:441–451` → calls
    `self.chat_executor.execute(&proto_req).await` at `robot_control.rs:452`.
  - `resolved` argument passed to `infer_response_topic` matches frontend form:
    lib.rs:63 `let topic = resolve_topic(req);` → lib.rs:100 `infer_response_topic(&topic)`.
    `resolve_topic` (lib.rs:207–215) prepends `/fleet/bot` derived from
    `apply_target_defaults` so the resolved topic **does** contain `/watch/` and **does**
    end with `/submit`, satisfying R3.
- Counterexample found: no. Not dead code; the primary `argo-gateway-server` binary calls
  it on every Chat RPC where `streaming=true`.

### V2.3 — Topic normalization: `action.replace(/\./g, "/")` aligns with backend subscription
- Finding: **PASS**
- Evidence:
  - Frontend `runChatCommand` at `packages/gateway-client/src/lib/demoRobotControl.ts:246`:
    `command: \`watch/${input.action.replace(/\./g, "/")}/submit\``. For
    `action = "lifecycle.execute"` (set by `runLifecycleExecute` line 278), produces
    `command = "watch/lifecycle/execute/submit"`.
  - ArgoGateway publishes the raw payload JSON to zenoh topic
    `/{fleet}/{bot}/watch/lifecycle/execute/submit` via
    `self.sdk.publish_json(&topic, &value, Profile::CommandChannel).await` at
    `lib.rs:78–81`. The `watch/` prefix is **kept**, not stripped.
  - Backend wildcard: `demo-app-backend/src/main.rs:170` —
    `let watch_topic = format!("/{fleet_id}/{bot_name}/watch/**");` subscribes via
    `sdk.subscriber::<serde_json::Value>().key(watch_topic)`. Zenoh `**` is recursive
    multi-segment; matches `…/watch/lifecycle/execute/submit` (3-segment tail, same depth
    as the 7 legacy).
  - Backend action extraction: `demo-app-backend/src/topic.rs:4-18
    extract_action_from_topic`. For `/demo/robot_1/watch/lifecycle/execute/submit`,
    split-filter gives `["demo","robot_1","watch","lifecycle","execute","submit"]`;
    `pos("watch")=2`, `start=3`, `parts.len()=6 > 4 ✓`, `parts.last()="submit" ✓`;
    returns `parts[3..5].join(".") = "lifecycle.execute"`. V1 verdict point 11 already
    independently verified this with `cargo test` — PASS.
- Counterexample found: no. Frontend's `watch/<x>/submit` → ArgoGateway publishes verbatim
  under `/fleet/bot/` prefix → backend's `/watch/**` wildcard catches → action derived
  back to `lifecycle.execute`. Round-trip lossless.

### V2.4 — Response topic alignment
- Finding: **PASS**
- Evidence:
  - ArgoGateway `infer_response_topic` returns
    `{prefix}/watch/lifecycle/execute/result` — preserved fleet/bot prefix via in-place
    `str::replace("/submit", "/result")` (lib.rs:225).
  - Backend has its own mirror at `demo-app-backend/src/topic.rs:22–36
    infer_reply_topic_for_submit`. For the same wire topic
    `/demo/robot_1/watch/lifecycle/execute/submit`:
    - R1 (`ends_with("/task/submit")`, topic.rs:23–25): false.
    - R2 (`contains("/watch/") && ends_with("/submit")`, topic.rs:26–28): true → returns
      `/demo/robot_1/watch/lifecycle/execute/result`. Identical string to ArgoGateway's.
  - Backend actually publishes the reply at `main.rs:222–227` —
    `sdk.publish_json(&reply_topic, &reply_json, Profile::CommandChannel).await`, with a
    leading-`/` normalization at `main.rs:212–214`.
  - ArgoGateway subscribes to the same derived topic at `lib.rs:112
    self.sdk.subscriber_json(&resp_topic).await` and waits up to `timeout_ms` at
    `lib.rs:124` for the response, returning it as `ChatResponse.data` at `lib.rs:126`.
- Counterexample found: no. Both sides independently derive the **same** response topic
  string from the same submit topic string.

### V2.5 — Comparison with existing 7 lifecycle topics
- Finding: **PASS**
- Evidence: the 7 legacy actions (`lifecycle.start`, `…stop`, `…restart`, `…list_groups`,
  `…list_state`, `…get_state`, `…group_restart`) all map via the same frontend helper to
  `watch/lifecycle/<verb>/submit` → resolved `/demo/robot_1/watch/lifecycle/<verb>/submit`.
  All 7 fire ArgoGateway R3, all 7 fire backend R2. The new `lifecycle.execute` →
  `watch/lifecycle/execute/submit` is structurally identical: same number of segments,
  same prefix, same suffix. dispatch_action's match arm at
  `demo-app-backend/src/handlers.rs:391–398` treats the 8th arm
  (`ACTION_LIFECYCLE_EXECUTE`) the same as the other 7 (bridged via
  `to_lifecycle_env(envelope)` then dispatched at handlers.rs:417–428).
- Counterexample found: no divergence between old 7 and new 1 under the Chat tunnel.

### V2.6 — Edge cases (adversarial)
- Finding: **PASS-with-notes** (no silent failures found; two forward-compat notes)
- Trailing slash. If frontend sent `action = "lifecycle.execute/"`, then
  `command = "watch/lifecycle/execute//submit"`. ArgoGateway `validate` (lib.rs:150–184)
  only rejects leading/trailing `/` on the full command (lib.rs:154) — the trailing `/`
  was stripped into the action prefix, not the full command. The charset check at
  lib.rs:157–163 allows `/` (it's in the allowed set), so double-slash passes validation.
  `infer_response_topic` still fires R3 (`contains("/watch/")` ✓, `ends_with("/submit")` ✓).
  Backend `extract_action_from_topic` uses `.split('/').filter(|s| !s.is_empty())`
  (topic.rs:5), which **collapses** the empty segment between the two slashes → still
  extracts `"lifecycle.execute"` correctly. Response topic does contain the literal
  double slash but both sides derive it with the same `replace("/submit","/result")`, so
  publish/subscribe still match. Behavior may be untidy but is not broken.
  **Not a real concern**: `runLifecycleExecute` hardcodes `action: "lifecycle.execute"`
  literal at demoRobotControl.ts:278; the trailing-slash parameterization path isn't
  reachable from the demo app.
- Case sensitivity. `validate` allows uppercase (`is_ascii_alphanumeric` at lib.rs:160
  covers `A-Z`). `contains("/watch/")` at lib.rs:224 is case-sensitive, so
  `"Watch/lifecycle/execute/submit"` would **not** fire R3; falls through to `None` at
  lib.rs:230 → caller at lib.rs:100–107 returns `"published"` without waiting for a
  response. Frontend hardcodes lowercase `watch/` at demoRobotControl.ts:246, so
  unreachable in practice.
- Forward-compat `lifecycle.execute.v2`. Maps to `watch/lifecycle/execute/v2/submit`.
  ArgoGateway R3 still fires → `watch/lifecycle/execute/v2/result`. Backend wildcard still
  catches. But `extract_action_from_topic` returns `"lifecycle.execute.v2"`, which
  `dispatch_action` at handlers.rs:380–429 does not match (falls into the outer `_ =>`
  arm → returns `UNKNOWN_ACTION` error envelope). Not silent — proper error response
  propagates back. **Note for Phase 3** forward-compat planning; not a Phase 2b blocker.
- Counterexample found: no silent drops. Malformed input produces either the same
  derived-topic pair or an explicit error envelope, never a vanished publish.

### V2.7 — `requestId` (correlation_id) propagation
- Finding: **PASS** (at the Chat protocol boundary — with one systemic note)
- Evidence:
  - Frontend `createRequestId()` at `demoRobotControl.ts:250` → `ChatRequest.requestId`
    (proto field).
  - Connect handler `robot_control.rs:442` — `request_id: gv1.request_id.clone()` —
    byte-exact clone into the proto `ChatRequest`.
  - `ChatExecutor::execute` at lib.rs:52–57 — uses `req.request_id` verbatim if non-empty,
    else generates a fresh `Uuid::new_v4()`. Bound into local `request_id` variable.
  - `make_resp` at lib.rs:233–240 — constructs `ChatResponse { request_id: request_id.to_string(), … }`.
    Every return path in `execute` goes through `make_resp(&request_id, …)`.
  - Hence `ChatResponse.request_id` (returned to frontend) equals `ChatRequest.requestId`
    (sent from frontend). Round-trip **unchanged** at the Chat protocol boundary.
- **Systemic note** (not a V2.7 failure): the zenoh hop does **not** propagate
  `request_id`. lib.rs:65–81 publishes only the parsed `req.payload` JSON — not the
  `request_id`. Backend `demo-app-backend/src/main.rs:187–206` attempts Envelope parse
  (fails, payload is raw) and rebuilds via `Envelope::new_request(&action, value)` at
  main.rs:204 — creating a **fresh** UUID in the backend envelope's `header.id`. Backend
  `handle_lifecycle_execute` then uses that fresh UUID as its `correlation_id` (V1
  verdict point 4 cites handlers.rs:839). So the three IDs —
  frontend `requestId`, ArgoGateway `request_id`, backend `correlation_id` — are **not**
  linked. This is a pre-existing systemic limitation of the Chat RPC tunnel inherited by
  all 8 lifecycle actions uniformly (legacy 7 + new 1). Not introduced by Phase 2a, not
  specific to `lifecycle.execute`, not in V2.7's PASS criterion. **Flag for Phase 3**
  planning vs. task.md acceptance B4 (`correlation_id 从 frontend → ArgoGateway → zenoh →
  demo-app-backend → provider 全链路传递`). See "Open judgment calls" below.

### V2.8 — ArgoGateway HEAD + sentry check
- Finding: **PASS**
- Evidence:
  - `git -C code/ArgoGateway rev-parse --abbrev-ref HEAD` = `feat/p9-lifecycle-unified-gateway` ✓
  - `git -C code/ArgoGateway rev-parse HEAD` = `da0bb4f2c5de41ce68b699a8abca95447ca75558` ✓
  - `git -C code/ArgoGateway status --short` — only 3 untracked baseline entries
    (`.understand-anything/`, `argogateway_0.1.0_amd64.deb`, `package-build-backups/`),
    matching the pre-existing baseline in the task prompt. **0 tracked changes.** ✓
  - `git -C code/ArgoWatch rev-parse HEAD` = `d2b3b9db685937313889cace8430fe86c43884a1` ✓
  - `sha256sum code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs`
    = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` ✓
  - `git -C code/frontend/robot-app-platform rev-parse HEAD` =
    `f7512bd94b4a9ef3c529407d75b8ed8f4bb14d02` on `feat/p9-lifecycle-unified-frontend` ✓
- Counterexample: no. All 4 sentries intact.

### V2.9 — 0 git push, 0 AI attribution, 0 code change
- Finding: **PASS**
- Evidence:
  - All git invocations during this session: `rev-parse --abbrev-ref HEAD`, `rev-parse HEAD`,
    `status --short`. **0 mutating git commands** (no add/commit/push/stash/reset/checkout).
  - `grep -r -E "Co-Authored|Co-authored|@anthropic|claude" src/` in ArgoGateway → 0 matches.
  - The verifier itself wrote 0 lines to any `.rs`, `.proto`, `.toml`, `.ts`, `.json`, or
    config file. Only artifact created: this `V2-GATEWAY-VERDICT.md`.
- Counterexample: no.

### V2.10 — Verifier self-honesty check
- Finding: **PASS**
- Evidence (specific citations):
  - Read `src/argo-gateway-chat/src/lib.rs` end-to-end (348 lines including `mod tests`
    through line 348). Key lines: 52–148 (`ChatExecutor::execute`), 217–231
    (`infer_response_topic` with R1–R4 at 218, 221, 224, 227), 207–215 (`resolve_topic`),
    150–184 (`validate`), 233–240 (`make_resp`).
  - Read `src/argo-gateway-server/src/robot_control.rs:435–460` — `async fn chat`, the
    Connect handler entry point that bridges gateway.v1 ↔ proto chat types and calls
    `chat_executor.execute(&proto_req)`.
  - Read `src/argo-gateway-server/src/main.rs:174` (ChatExecutor construction, via grep).
  - Read `demo-app-backend/src/main.rs:130–240` — subscribe loop (`watch_topic` at 170,
    Envelope vs raw-payload fallback at 187–206, `infer_reply_topic_for_submit` at 208,
    reply publish at 222–227).
  - Read `demo-app-backend/src/topic.rs` end-to-end (89 lines) — `extract_action_from_topic`
    at 4–18, `infer_reply_topic_for_submit` at 22–36, unit tests at 38–89.
  - Read `demo-app-backend/src/handlers.rs:375–435` — `dispatch_action` outer match arm
    covering all 8 lifecycle actions at 391–398, inner dispatch table at 417–428.
  - Read `packages/gateway-client/src/lib/demoRobotControl.ts:230–290` — `runChatCommand`
    at 239–258 (action.replace at 246, createRequestId at 250), `runLifecycleExecute` at
    271–283.
- Full call trace (single RPC):
  1. Frontend `runChatCommand` POSTs Connect `ChatRequest{request_id, command:"watch/lifecycle/execute/submit", payload:"{\"op\":...}"}`.
  2. `robot_control.rs:437 async fn chat` receives gateway.v1 ChatRequest.
  3. `robot_control.rs:441–451` converts to proto `ChatRequest` byte-exact (incl. `request_id` clone at :442).
  4. `robot_control.rs:452` → `chat_executor.execute(&proto_req)`.
  5. `lib.rs:52 ChatExecutor::execute` → `lib.rs:53–57` derive `request_id` local → `lib.rs:63 resolve_topic` → `/demo/robot_1/watch/lifecycle/execute/submit`.
  6. `lib.rs:78–81` `publish_json` to zenoh topic above with payload JSON.
  7. `lib.rs:100` `infer_response_topic(&topic)` → R3 → `/demo/robot_1/watch/lifecycle/execute/result`.
  8. `lib.rs:112` `subscriber_json(&resp_topic)` → `lib.rs:124` timeout-wait.
  9. Backend `main.rs:170` wildcard `/demo/robot_1/watch/**` catches the publish.
  10. `main.rs:199–205` raw-payload branch → `extract_action_from_topic` → `"lifecycle.execute"` → `Envelope::new_request(&action, value)`.
  11. `main.rs:216` `dispatch_action(&envelope, &config, &rt)` → handlers.rs:398 outer arm → handlers.rs:427 `handle_lifecycle_execute(rt, &lc_req).await`.
  12. `main.rs:222–227` publishes reply Envelope JSON to `/demo/robot_1/watch/lifecycle/execute/result`.
  13. ArgoGateway `lib.rs:124–126` receives → `make_resp(&request_id, OK, "ok", v.to_string())` → returns ChatResponse with the **original** frontend `request_id`.
- V1 cross-reference: V1 verdict points 11 (topic.rs extract) + 12 (main.rs wildcard)
  already proved backend catches the topic and parses the action; V2.3 + V2.4 verified
  ArgoGateway's side mirrors the derivation logic. V1 point 4 (correlation via
  `clone_req_with_action`) confirms backend propagates whatever `header.id` the envelope
  carries — V2.7 confirms the envelope gets a fresh UUID at the zenoh hop, independent
  of frontend `requestId`.
- Counterexample: none identified.

## ESCALATEs from V2 verifier

None blocking. One advisory observation for Phase 3 planning (not a Phase 2b blocker):

- **Advisory (not an ESCALATE)** — zenoh correlation_id gap: the Chat RPC tunnel drops
  `request_id` at the zenoh publish step. Task.md acceptance B4 for Phase 3
  requires `correlation_id` to flow frontend → ArgoGateway → zenoh → backend → provider.
  Under Scheme A, that chain will be broken at the ArgoGateway → zenoh step: backend
  reconstructs a fresh UUID. Options for Phase 3 (orchestrator's call, not this
  verifier's): (a) extend `runLifecycleExecute`'s payload to embed a `request_id` field
  that `handle_lifecycle_execute` reads (still no proto change); (b) move to Scheme B
  (typed `LifecycleExecute` RPC with envelope-preserving header) when adding proto
  in a later phase; (c) accept the gap and document it. **Recommend deferring this
  decision to Phase 3 kickoff — do not patch ArgoGateway for it under D-014.**

## Verifier's open judgment calls

- **Treating `apply_target_defaults`+`resolve_topic` prefix as in-scope for R3**: V2.1's
  prompt text traces rule-matching against the bare frontend form
  `"watch/lifecycle/execute/submit"`, but the actual call passes the resolved topic with
  fleet/bot prefix. Conservative read: cite both forms — R3 fires under either since
  `contains("/watch/")` is prefix-agnostic. Documented in V2.1 trace above.
- **Treating V2.6 trailing-slash as "not a real concern"**: `runLifecycleExecute` passes
  a literal `"lifecycle.execute"` (demoRobotControl.ts:278), so parameterization that
  could produce a trailing slash isn't reachable from the shipped code path. Flagged
  but not escalated.
- **Treating V2.7 as PASS while flagging the systemic zenoh gap**: V2.7's PASS criterion
  is "`request_id` round-trips through ArgoGateway unchanged", which is satisfied at
  the Chat protocol layer. The zenoh-layer drop is pre-existing, uniform across all 8
  lifecycle actions, and invisible to the REFACTOR acceptance criteria. Marked PASS with
  advisory note rather than FAIL (which would incorrectly flag Scheme A as broken for
  behavior that was never its goal) or ESCALATE (which would override D-014's "0
  ArgoGateway change" intent for a problem D-014 didn't claim to solve).
- **Not running cargo test or live Chat RPC**: the prompt explicitly forbids code
  execution (C4 "0 mock test"); all verification is by source reading + call tracing.
  Two unit tests already exist at lib.rs:296 (`infer_response_topic_task_submit`) and
  lib.rs:303 (`infer_response_topic_roboskill`), but neither covers `/watch/`; adding
  one would require a code change → explicitly out of write-set.

## Final verdict recommendation

**ACCEPT** — Phase 2b verifier finds **zero ArgoGateway code change required** for
`lifecycle.execute` to route through the Chat RPC tunnel. D-014 (Scheme A) is sound.

The existing generic R3 rule at `src/argo-gateway-chat/src/lib.rs:224-226` covers the
new topic identically to the 7 legacy lifecycle topics. Frontend's `runChatCommand`
delivers a well-formed `watch/lifecycle/execute/submit`, ArgoGateway publishes verbatim,
backend wildcard catches, backend mirrors ArgoGateway's response-topic derivation, and
ArgoGateway returns the response with the original `request_id` intact.

**Hand-off to Phase 3**:
- Carry forward ESCALATE-2a-1 (service_id payload fill for Start/Stop/Restart/GetState
  ops on SP000065).
- Itemize the zenoh correlation_id gap (V2.7 systemic note) for orchestrator decision:
  embed `request_id` in payload, move to Scheme B, or accept the gap.
- Real-robot E2E on SP000065 remains the proving ground for the full
  frontend → ArgoGateway → zenoh → backend → lifecycle → provider chain.
