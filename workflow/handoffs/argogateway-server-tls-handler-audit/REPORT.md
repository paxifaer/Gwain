# REPORT — Gateway server `PushZenohRouterConfig` handler audit (orchestrator's judgment)

## Task
`argogateway-server-tls-handler-audit` — audit the gateway server's
`PushZenohRouterConfig` handler to de-risk E1 (does server reject the new
`transport` block via `deny_unknown_fields`?) and verify Option A (does
server translate the block into env-file TLS deltas D4–D14?).

## Workers dispatched
- **W1** (audit, general-purpose Agent, ~30 min) — found server source,
  read handler, gave E1 + Option A verdicts, discovered BLOCKER 1 + BLOCKER 2.
- **V1** (verifier, general-purpose Agent, ~45 min, adversarial mandate) —
  re-ran searches, opened every cited file:line, traced the frontend's TLS
  config through the validator by hand, found NEW BLOCKER 3 (stale deployed
  deb) + 3 missing code paths W1 missed.

## Verdict chain
- **W1**: E1=SAFE, Option A=NOT-IMPLEMENTED, plus BLOCKER 1 (validate_router
  rejects TLS endpoints) and BLOCKER 2 (health check polls 57447 only).
  Risk summary: NOT safe to deploy as-is.
- **V1**: `ACCEPT W1` — 28 claims upheld, 1 overturned (Claim 13 "exactly
  ONE writer" — there are 5, but only install_cluster.sh writes TLS deltas),
  4 nuanced (line-number off-by-2-to-8; TLS code on `feat/argo-tls` not
  `origin/main`; 9252dda IS merged; deb freshness). 0 fabricated citations.
  UPHOLD on all four headline verdicts. **V1 discovered NEW BLOCKER 3** that
  strengthens W1's "NOT safe to deploy" verdict.
- **Orchestrator judgment**: **ACCEPT W1** (with V1's BLOCKER 3 added to
  the picture).

## Headline answer — much worse than the prior audit expected

The frontend change is **NOT safe to deploy as-is**, and the blockers are
not the ones E1 was worried about. The original E1 risk (`deny_unknown_fields`)
is a false alarm — the server uses `serde_json::Value` (dynamic JSON) at
both layers and accepts any field. But the audit found **three** server-side
blockers, in order of severity:

### BLOCKER 3 (V1's new finding — most severe)
The currently-deployed `argogateway_0.1.0_amd64.deb` at
`ArgoDeploy/packages/` was built **June 30** and has **ZERO**
`PushZenohRouterConfig` / `argodds_tools` symbols — it predates the handler
(commit `b98f1e2` that added the RPC) by ~6 weeks. On robots running the
currently-deployed deb, the `PushZenohRouterConfig` RPC fails with
`UNIMPLEMENTED` **before BLOCKER 1/2 even apply**.

A **newer** `argogateway_0.1.0_amd64.deb` was built **Aug 18** and exists at
`ArgoGateway/` — but it is NOT in `ArgoDeploy/packages/`, so
`install_cluster.sh` still installs the older June 30 deb. The build pipeline
is out of sync with the deploy pipeline.

### BLOCKER 1 (UPHOLD by V1)
`argodds-tools`'s `validate_router` at `manager.rs:625-631` does a strict
equality check `e.as_str() == Some("tcp/0.0.0.0:57447")` on each
`listen.endpoints` entry. The frontend's TLS-mode config
(`["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]`) contains no such endpoint,
so the validator returns `Err("router.listen.endpoints must contain
\"tcp/0.0.0.0:57447\"")`. TLS-mode pushes fail at validation.

### BLOCKER 2 (UPHOLD by V1)
`argodds-tools`'s `restart_and_healthcheck` at `manager.rs:554` does
`text.contains("0.0.0.0:57447")` on `ss -tln` output. TLS mode listens on
57448/57449, not 57447, so the health check never matches. After a 5s
timeout, the restart rolls back to the previous config.

### Option A (UPHOLD by V1)
NOT-IMPLEMENTED. The `argodds-tools` daemon reads env only in its `report()`
function (for `BOT_NAME` / `FLEET_ID`); there is no `write_env_file` function.
The 11 env-file TLS deltas (D4–D14: `GATEWAY_TLS_ENABLE`,
`GATEWAY_TLS_PORT`, `GATEWAY_TLS_CERT_PATH`, `GATEWAY_TLS_KEY_PATH`,
`GATEWAY_TLS_ROOT_CA_PATH`, `GATEWAY_TLS_CA_CERT_PATH`,
`GATEWAY_TLS_DOMAIN`, `GATEWAY_GRPC_ENABLE=0`, `GATEWAY_URL=https://...`,
`ZENOH_ENDPOINT=tcp/127.0.0.1:57449`, `ZENOH_GLOBAL_ENDPOINT=...`) are
written only by `install_cluster.sh` — an out-of-band SSH/SCP step. The
server-side handler does NOT derive them from the received config.

### E1 (UPHOLD by V1 — false alarm)
SAFE. The handler at `robot_control.rs:462-511` parses `config_json5` as
`serde_json::Value` (line 474) — dynamic JSON, accepts any field. The
`argodds-tools` daemon's parser at `argodds_tools/server.rs:35` is also
`serde_json::Value`. Zero `deny_unknown_fields` attributes anywhere in the
workspace (V1 grep-confirmed). The new `transport` top-level field the
frontend emits will be accepted by the parser. **E1 was the wrong risk to
worry about — the real blockers are elsewhere.**

## What the server actually does with `PushZenohRouterConfig`
1. `robot_control.rs:462-511` (ArgoGateway server) receives the RPC,
   extracts `config_json5` string, parses as `serde_json::Value`, forwards
   to the embedded `argodds-tools` daemon (co-resident in `demo-app-backend`).
2. `argodds_tools/server.rs:35` (daemon) receives the JSON Value.
3. `manager.rs:625-631` validates the config — **rejects TLS endpoints**
   (BLOCKER 1).
4. Daemon writes the config to `/etc/argo-zenoh/zenohd-global.json5` (+ meta
   + history).
5. Daemon restarts `argo-zenoh-global.service`.
6. `manager.rs:554` health-checks by polling `ss -tln` for 57447 — **fails
   for TLS** (BLOCKER 2), rolls back.
7. Daemon does NOT write `/etc/argo-gateway/env` (Option A NOT-IMPLEMENTED).

The `metadata` field (where the frontend now sets `tls_mode: "tls" |
"plaintext"`) is **dead data at the server side** — the server does not read
it.

## Source location (V1 confirmed)
- Server source: `/home/wangdang/work/ai-stack/code/ArgoGateway/` (Rust workspace)
- Handler: `src/argo-gateway-server/src/robot_control.rs:462-511`
- Daemon: `argodds-tools` embedded in `demo-app-backend`. Source on
  `origin/main` of `code/ArgoWatch/` (NOT on current branch
  `feat/lifecycle-robot-takeover` — read via `git show origin/main:`).
- V1 noted: TLS-related code in `main.rs:268-320` is on `feat/argo-tls`
  branch, not `origin/main`. Multiple TLS-related branches in flight — the
  user needs to decide which branch is the production source of truth.

## Missing code paths V1 found (W1 missed)
1. **`install.sh`** (separate from `install_cluster.sh`) — additional
   plaintext-only env writer. Not in W1's read set. Not a TLS-mode concern
   but worth knowing about for the full env-file picture.
2. **Newer Aug 18 `argogateway_0.1.0_amd64.deb`** at `ArgoGateway/` — has
   the handler + TLS code. But `ArgoDeploy/packages/` has the older June 30
   deb, which is what `install_cluster.sh` actually installs. Build/deploy
   pipeline out of sync.
3. **`skyline-cloud-gateway-server`** — a Go service. V1 confirmed it has
   no `PushZenohRouterConfig` handler — irrelevant to this audit.

## To make the frontend change actually work end-to-end
The user needs to commission (in this order, each is a separate task):

1. **Sync the deb build pipeline** — copy the Aug 18 deb from `ArgoGateway/`
   to `ArgoDeploy/packages/` (or change `install_cluster.sh` to install
   from `ArgoGateway/`). Without this, BLOCKER 3 stands on every deployed
   robot — the RPC is `UNIMPLEMENTED` before any other fix can take effect.

2. **Relax `validate_router`** in `argodds-tools` `manager.rs:625-631` —
   accept TLS-shaped `listen.endpoints` (must contain `tls/0.0.0.0:57448`
   when `transport.link.tls` is present; still require `tcp/0.0.0.0:57447`
   when not). Closes BLOCKER 1.

3. **Fix `restart_and_healthcheck`** in `manager.rs:554` — poll for the
   actual configured endpoints (57447 for plaintext, 57448/57449 for TLS),
   not hardcoded 57447. Closes BLOCKER 2.

4. **Implement Option A** — server-side env derivation. When the received
   config has a `transport.link.tls` block, the daemon writes the 11
   env-file deltas (D4–D14) to `/etc/argo-gateway/env` and restarts
   `argogateway.target`. Without this, the frontend TLS toggle writes the
   zenoh config but the gateway's own env still says plaintext —
   half-broken TLS.

5. **Decide on `feat/argo-tls` vs `origin/main`** — V1 noted TLS code in
   `main.rs:268-320` is on `feat/argo-tls`, not `origin/main`. The user
   must decide which branch is the production source of truth before any
   server-side changes are committed.

6. **Optional: read `tls_mode` metadata** at the server side. Today the
   frontend sets `metadata: {operator, tls_mode}` but the server doesn't
   read `tls_mode`. Either read it (and use it as a signal alongside the
   `transport.link.tls` block presence) or stop setting it (frontend
   cleanup).

## ESCALATEs forwarded to user

From W1 (7) — all UPHOLD by V1 except as noted:
1. `validate_router` rejects TLS endpoints — **BLOCKER 1, UPHOLD**
2. Health check polls 57447 — **BLOCKER 2, UPHOLD**
3. argodds-tools source only on `origin/main` — UPHOLD; `9252dda` IS merged
   (V1 confirmed)
4. `tls_mode` metadata is dead data at server — UPHOLD
5. `argo-zenoh-global.service` unit name not verified against deployed deb
   — V1 did not explicitly verify; left as soft ESCALATE
6. argodds-tools co-resident with demo-app-backend; no independent supervisor
   — UPHOLD
7. Other robot-side services not exhaustively checked for env writers — V1
   did a broader grep and found `install.sh` (plaintext-only) +
   `skyline-cloud-gateway-server` (no handler); both irrelevant to TLS

From V1 (new):
8. **BLOCKER 3**: deployed deb is stale (June 30) — RPC `UNIMPLEMENTED` on
   production robots. Newer Aug 18 deb exists but isn't in the deploy
   pipeline.
9. TLS code on `feat/argo-tls`, not `origin/main` — which branch is
   production?
10. Line-number drift: W1's citations are off by 0-8 lines from V1's
    readings — minor, semantic claims all hold.

## Files produced by this task
- `handoffs/argogateway-server-tls-handler-audit/SPEC.md`
- `handoffs/argogateway-server-tls-handler-audit/PROMPT-W1.md`
- `handoffs/argogateway-server-tls-handler-audit/W1-REPORT.md` (W1 output)
- `handoffs/argogateway-server-tls-handler-audit/V1-VERDICT.md` (V1 output, 301 lines)
- `handoffs/argogateway-server-tls-handler-audit/REPORT.md` (this file)

## Decision for the user
The audit is judged **ACCEPT**. The frontend change (D1+D2 in
`robot-app-platform`) is correctly implemented but cannot function
end-to-end without server-side work. Recommended next tasks, in priority
order:

1. **Sync deb build → deploy pipeline** (BLOCKER 3 — highest priority;
   without this, nothing else matters).
2. **Server-side: relax `validate_router` + fix `restart_and_healthcheck`**
   (BLOCKER 1 + 2 — single task touching `argodds-tools/manager.rs`).
3. **Server-side: implement Option A** (env-file derivation — larger task
   touching daemon + systemd unit restart logic).
4. **Decide `feat/argo-tls` vs `origin/main`** as production branch (user
   decision, not a worker task).

Each is a separate Gawain task with its own SPEC + W1 + V1 + judge cycle.
The user can dispatch them in parallel (1+4) or serially (2 depends on 1, 3
depends on 2).
