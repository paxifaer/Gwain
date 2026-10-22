# REPORT — ArgoGateway TLS-mode config audit (orchestrator's judgment)

## Task
`argogateway-tls-config-audit` — investigate whether `robot-app-platform`'s
"click TLS" UX produces a different ArgoDDS / ArgoGateway config in TLS mode,
in every place where `ArgoDeploy/real/install_cluster.sh` also branches on TLS.

## Workers dispatched
- **W1** (investigation, general-purpose Agent, foreground) — read
  `install_cluster.sh` + `robot-app-platform` source; produce gap analysis.
- **V1** (verifier, general-purpose Agent, adversarial mandate) — disprove W1's
  claims by re-opening every cited file:line.

## Verdict chain
- **W1**: `GAP` — 14 TLS deltas in `install_cluster.sh`, 0 mirrored in
  `robot-app-platform`, 14 gaps, 0 partial.
- **V1**: `CONFIRM` — all 7 key claims upheld, 0 overturned, 1 nuanced (claim 4
  wording, not substance), 0 missing deltas, 0 fabricated citations,
  0 re-interpreted `NO`s that are actually `YES`/`PARTIAL`.
- **Orchestrator judgment**: **ACCEPT W1**. V1's adversarial check passed; the
  evidence satisfies the SPEC's acceptance criteria.

## Headline answer to the user
**Yes — there is a gap.** The frontend's "使用 TLS 加密" checkbox in
`AddRobotDialog.tsx` only flips the CLIENT-side HTTP URL between
`https://<host>:50053` and `http://<host>:50051`. It does NOT cause the
frontend to generate a different ArgoDDS / ArgoGateway server config. The
sole server-config surface — `buildZenohRouterConfig()` in
`zenohRouterConfig.ts` (demo + skyline twins) — always emits a fixed
plaintext-shaped config (`tcp/0.0.0.0:57447` listen, no `transport.link.tls`
block). The frontend also has no code path that writes `/etc/argo-gateway/env`
at all, so 11 of the 14 install_cluster.sh TLS deltas (the env-file ones) are
structurally unmirrored.

## Gap matrix (condensed — full version in W1-REPORT.md §5)
| Delta | What install_cluster.sh does in TLS mode | Mirrored in frontend? |
|---|---|---|
| D1 | zenohd-global listens on `["tcp/127.0.0.1:57449","tls/0.0.0.0:57448"]` | NO |
| D2 | zenohd-global gets `transport.link.tls{listen_certificate, listen_private_key, root_ca_certificate, enable_mtls:false}` | NO |
| D3 | cert file perms on `/etc/argo-tls/*` | NO |
| D4–D14 | 11 env-file deltas in `/etc/argo-gateway/env` (`GATEWAY_TLS_ENABLE=1`, `GATEWAY_TLS_PORT=50053`, `GATEWAY_TLS_CERT_PATH`, `GATEWAY_URL=https://...`, `ZENOH_ENDPOINT=...:57449`, `GATEWAY_GRPC_ENABLE=0`, etc.) | NO |

## Minimal fix recommendation (W1 §7,endorsed by V1)
1. **Frontend D1 + D2**: extend `ZenohRouterConfig` type + `buildZenohRouterConfig`
   to accept a TLS flag; emit `listen.endpoints: ["tcp/127.0.0.1:57449","tls/0.0.0.0:57448"]`
   + the `transport.link.tls{...}` block when TLS is on. Add a TLS toggle to
   `NetworkConfigDialog` (or derive from target robot's `tlsStatus`). Relax
   `validateZenohRouterConfig` so it doesn't reject TLS-shaped configs.
2. **Server-side D4–D14 (Option A)**: let the gateway server derive the
   env-file TLS deltas from the `transport.link.tls` block in the received
   zenohd-global config. No frontend code for env files — keeps frontend thin
   and avoids duplicating `install_cluster.sh:124–170` in TypeScript.
3. **D3 (cert perms)**: keep as out-of-band SSH/SCP step (already the script's
   own comment at `install_cluster.sh:104–105` says cert files are deployed
   via scp). Document; don't try to automate via gRPC.

## ESCALATEs forwarded to user
W1 raised 7 judgment calls; the three that may need user input:

- **E1**: "Click TLS" was read as the "使用 TLS 加密" checkbox in
  `AddRobotDialog.tsx`. If the user meant a *planned but unbuilt* TLS toggle
  in `NetworkConfigDialog`, the verdict is still GAP (no such toggle exists
  today).
- **E2**: Whether the gateway server already translates a `transport.link.tls`
  block (if the frontend ever emitted one) into the `/etc/argo-gateway/env`
  deltas is OUT OF SCOPE — the audit read set was restricted to
  `install_cluster.sh` + `robot-app-platform`. If a Develop worker is
  dispatched, this server-side translation must be checked before assuming
  Option A is sufficient.
- **E3**: `metadata` field in `PushZenohRouterConfigRequest` is free-form
  `map<string,string>`. Only call site sets `{operator:"demoapp"}`. If a
  hidden caller passes a TLS metadata key, the server could already be
  deriving TLS state — not visible in today's frontend code.

## Files produced by this task
- `handoffs/argogateway-tls-config-audit/SPEC.md`
- `handoffs/argogateway-tls-config-audit/PROMPT-W1.md`
- `handoffs/argogateway-tls-config-audit/W1-REPORT.md` (W1 output)
- `handoffs/argogateway-tls-config-audit/V1-VERDICT.md` (V1 output)
- `handoffs/argogateway-tls-config-audit/REPORT.md` (this file — orchestrator judgment)

## Decision for the user
- Accept the audit as-is, OR
- Dispatch a Develop worker to implement the minimal fix (D1+D2 in frontend
  + server-side env derivation), OR
- Expand the audit scope to include the gateway server-side code that handles
  `PushZenohRouterConfig` (to de-risk Option A before committing to it).
