# Propagation — Correlation ID and Run ID Across Boundaries

**Component:** 传播 / Propagation — how `correlation_id` and `run_id`
cross process, protocol, and machine boundaries without breaking
the trace.

## `correlation_id` — one per business operation

Generate one `correlation_id` per business operation at the
**entry-point service** (the service that receives the user/system
trigger — a button click, a cron tick, a webhook delivery). Propagate
it across every hop. The verifier greps `corr=<id>` to reconstruct
the full trace.

### Generation rule

- **Entry-point service**: generate a fresh `correlation_id` when the
  business operation starts. Format: `corr-<6hex>` (e.g.
  `corr-7f3a9c`). Use a cryptographically random source if available;
  fall back to `uuid4().hex[:6]` or `rand::random::<u32>()`.
- **Downstream services**: read the inbound `correlation_id` from
  the transport-specific mechanism (below). Do NOT generate a new
  one. If the inbound had no `correlation_id`, generate one AND log
  a STATE event: `from_state=no_corr to_state=corr_assigned
  reason=inbound_missing_corr`.

### Propagation by transport

| Transport | How `correlation_id` crosses | Notes |
|---|---|---|
| HTTP | Request header `X-Correlation-Id` | Both directions: the response SHOULD echo it back so the caller can correlate async. |
| gRPC / RPC | Metadata key `correlation-id` | Lowercase, hyphenated. gRPC metadata is case-insensitive but the convention is lowercase. |
| zenoh | User properties OR key suffix `/<correlation_id>/` | zenoh has no HTTP-style headers; use the keyexpr to embed `corr` OR use zenoh's user-properties attachment. |
| Tauri invoke | Argument field `correlationId` (camelCase, JS convention) | The Tauri command's args struct MUST include this field; the Rust handler reads it. This is the `argo_tls.rs` bug class — without it, the rejection's cause is lost across the JS↔Rust boundary. |
| WebSocket | First message field OR subprotocol header | If using subprotocol: `Sec-WebSocket-Protocol: corr-<id>`. If using first message: the first JSON the client sends includes `correlationId`. |
| Inter-process (IPC, mpsc, channels) | Message header field | Every message struct on the channel carries `correlation_id` as a field. Channels that pass `Vec<u8>` (raw bytes) MUST prefix a fixed-size header containing `corr`. |

### What "propagates" means

A service that receives a request with `correlation_id` MUST:
1. Read it from the inbound transport.
2. Include it on every outbound call to downstream services.
3. Include it on every log event it emits while handling this
   request (FAIL, ERROR, STATE, DEBUG).
4. Echo it on the response (where the transport supports it) so
   the caller can correlate async callbacks.

If any of these is missing, the trace is broken. The verifier
reconstructs the chain by following `correlation_id` hop-by-hop;
a gap means a service in the middle dropped it.

### Inbound without `correlation_id`

If a request arrives without `correlation_id`:

1. The receiving service generates one.
2. It logs a STATE event: `from_state=no_corr
   to_state=corr_assigned reason=inbound_missing_corr` (with the
   fresh `correlation_id` on the line).
3. From that point on, the service treats the freshly assigned
   `correlation_id` as if it had been propagated.

**Exception:** the very first entry-point assignment STATE event (the
one that starts a business operation) is the only STATE event that
is allowed to NOT have a prior `correlation_id`. Every subsequent
event — including subsequent `corr_assigned` events for other
inbound-without-corr requests — MUST have `correlation_id`.

## `run_id` — one per integration test run

`run_id` propagates via environment variable `GAWAIN_RUN_ID`. All
services in the same test run read the same value at startup. If
absent (production), log `run_id=prod` or derive from a deployment
id (e.g. k8s pod namespace + deployment name).

### Set at integration test launch

The integration test harness (or the worker running the test) sets
`GAWAIN_RUN_ID` before spawning any service:

```bash
export GAWAIN_RUN_ID=run-20260818-001
# then launch all services: frontend, gateway, backend, cloud, robot
```

Format: `run-<YYYYMMDD>-<seq>` (e.g. `run-20260818-001`).

### Read at service startup

Each service reads `GAWAIN_RUN_ID` at startup and stamps it on
every log event. Services MUST NOT generate `run_id` themselves —
if `GAWAIN_RUN_ID` is unset, they log `run_id=prod` (or a
deployment-derived value), NOT a random one. The verifier's
**scope completeness check** (see [`evidence.md`](evidence.md))
flags any service in the run that logged `run_id=prod` while
others logged `run-20260818-001` — that's a misconfigured
service that wasn't wired to the test harness.

### Cross-process propagation of `run_id`

`run_id` does NOT need to propagate per-request. It is
process-level state set at startup. Every event from a given
process instance has the same `run_id`. This is the difference
from `correlation_id` (which is per-request and crosses every
boundary).

## `attempt` — 1-indexed retry counter

`attempt` is a **per-hop retry counter at the entry service**.
Default value is `1` (no retry).

### Semantics

- The entry service starts at `attempt=1`.
- On retry (within the entry service's retry budget), it
  increments its own `attempt` to `2`, `3`, ... before
  re-issuing the call.
- The downstream service **sees the propagated `attempt` and
  does NOT increment it**. If the entry service's `attempt=2`
  retry reaches a downstream service, that service logs
  `attempt=2` for everything it does while handling this
  request.
- If the downstream service has its own retry budget to a
  further-downstream service, that's a NESTED retry counter
  (out of scope for this contract; P1). The downstream service
  MUST continue to log the entry service's `attempt` on all
  events for traceability; nested retry budget is a separate
  concern.

### Why downstream does NOT increment

If every hop incremented `attempt`, the verifier could not tell
whether `attempt=3` means "the entry service retried 3 times" or
"the call went 3 hops deep". Pinning `attempt` to the entry
service's retry counter makes it unambiguous: `attempt=3` always
means "third attempt by the entry service".

### `phase=retry` vs `phase=retry_exhausted`

- `phase=retry` on a FAIL means "this is a FAIL on a retry
  attempt; the budget is NOT yet exhausted". Logged by the
  entry service when a retry attempt itself fails.
- `phase=retry_exhausted` on a FAIL means "the retry budget is
  spent; this is the final FAIL the entry service will surface
  for this operation". **Every retry-budget exhaustion MUST
  emit a FAIL with `phase=retry_exhausted`** — silently giving
  up is a contract violation.

### Example attempt trace

```
attempt=1 service=frontend caller=frontend callee=gateway phase=timeout   # 1st attempt timed out
attempt=2 service=frontend caller=frontend callee=gateway phase=request    # 2nd attempt started
attempt=2 service=frontend caller=frontend callee=gateway phase=timeout    # 2nd attempt timed out
attempt=3 service=frontend caller=frontend callee=gateway phase=request    # 3rd attempt started
attempt=3 service=frontend caller=frontend callee=gateway phase=timeout    # 3rd attempt timed out
attempt=3 service=frontend caller=frontend callee=gateway phase=retry_exhausted  # budget spent
```

The verifier greps `phase=retry_exhausted` to find the final
FAIL; greps `corr=<id>` to find the whole chain; uses `attempt`
to count how many retries happened.
