# Events — Taxonomy, Mandatory Log Points, and First-Failure Principle

**Component:** 事件 / Events — the three event kinds, their specific
fields, when each fires, and how the verifier reconstructs the
"first failure" from a cascade.

## Event taxonomy (mutually exclusive)

- **FAIL** = cross-boundary call did not meet contract. Examples:
  TCP/UDP handshake fail, connect refused, HTTP 4xx/5xx from peer,
  RPC timeout, schema mismatch, TLS cert reject, command ack
  timeout, control loop overrun.
- **ERROR** = internal invariant violated. Examples: panic, unwrap
  on None, asserted type mismatch, resource exhaustion
  (pool/thread/queue), corrupted state.
- **STATE** = state machine transition. Examples:
  idle→in_progress→done, pending→applied→rejected,
  connected→disconnected, healthy→degraded.

**Tiebreak:** when an event straddles two categories, prefer FAIL
(cross-boundary wins). A TCP handshake that also exhausted the
connection pool is a FAIL (cross-boundary), not an ERROR (pool
exhausted). The verifier's reconstruction starts from FAILs.

## FAIL-specific fields (in addition to common fields in [`context.md`](context.md))

Every FAIL event log line MUST also contain:

| # | field | meaning | example |
|---|-------|---------|---------|
| 9 | `caller→callee` | logical service names, NOT IPs | `frontend→gateway` |
| 10 | `operation` | call verb + subject | `POST /api/cmd`, `zenoh pub cmd/vel` |
| 11 | `phase` | `request` \| `response` \| `handshake` \| `timeout` \| `retry` \| `retry_exhausted` | `timeout` |
| 12 | `peer_addr` | physical address, supplementary (NOT primary identity) | `10.0.0.2:443` |
| 13 | `device_id` | robot fleet id (robot scene mandatory, others optional) | `SP000056` |
| 14 | `latency_ms` | numeric, `-1` if not measurable | `5000` |
| 15 | `error_class` | failure classification | `Timeout`, `UpstreamTimeout`, `RetryExhausted`, `ConnectionRefused`, `CertReject` |
| 16 | `error_message+cause` | full message + chained cause; NEVER `String(error)` | `timeout 5000ms` cause=`peer not responding` |

### Phase enum

- `request` — failure sending the request (connect refused, handshake
  failed before sending).
- `handshake` — TLS/SASL/auth handshake failed.
- `response` — request was sent, peer responded with an error
  (4xx/5xx, schema mismatch, application error).
- `timeout` — request was sent, no response within budget (first
  attempt).
- `retry` — retry attempt was dispatched (informational, often paired
  with a STATE event, but the FAIL on a retry attempt uses this).
- `retry_exhausted` — the retry budget is spent, the entry-point
  service surfaces this as the final FAIL. **Every** retry-budget
  exhaustion MUST emit a FAIL with `phase=retry_exhausted`. A
  sequence of FAILs ending without `phase=retry_exhausted` means the
  worker either gave up silently or didn't track retry budget — both
  are contract violations.

### `peer_addr` vs identity

`peer_addr` is the physical address (IP:port) of the peer — useful
for network-level debugging ("the peer at 10.0.0.2:443 rejected the
TLS cert"). It is **supplementary**. The primary identity is
`service` (common field, see [`context.md`](context.md)) +
`instance_id` (common) + `device_id` (scene-specific). If the
verifier needs to reconstruct a trace and the only way to find an
event is by `peer_addr`, the contract is broken.

### `device_id` on robot scene

Robot fleet identity (e.g. `SP000056`) is stable across robot
lifetime — far more stable than IP. On the robot scene
(robot↔gateway, robot↔cloud commands), `device_id` is **mandatory**
on every FAIL event. On non-robot scenes (frontend↔backend, cloud
RPC), `device_id` is optional.

## ERROR-specific fields (in addition to common)

Every ERROR event MUST also contain:

| # | field | meaning | example |
|---|-------|---------|---------|
| 17 | `invariant` | what was violated | `pool_size > 0` |
| 18 | `actual_value` | what was found | `0` |

ERRORs do NOT carry `caller→callee`/`operation`/`phase` — they are
internal. If an ERROR is caused by a cross-boundary call, the FAIL
event for that call is logged separately; the ERROR's `correlation_id`
links them.

## STATE-specific fields (in addition to common)

Every STATE event MUST also contain:

| # | field | meaning | example |
|---|-------|---------|---------|
| 19 | `from_state` | previous state | `idle` |
| 20 | `to_state` | new state | `in_progress` |
| 21 | `reason` | why the transition happened (optional but recommended) | `button_click`, `ack_timeout`, `healthcheck_fail` |

The `reason` field is new (P1, recommended but not mandatory). It
makes the transition greppable by cause: `grep reason=ack_timeout`
finds every transition triggered by an ack timeout across the
fleet.

## Level rules

| Event                  | Level | Notes                                           |
|------------------------|-------|-------------------------------------------------|
| FAIL                   | ERROR | Always                                          |
| ERROR                  | ERROR | Always                                          |
| STATE                  | INFO  | High-frequency STATE (e.g. heartbeat) may drop to DEBUG |
| Cross-boundary success | DEBUG | Not required, default off                       |

FAIL/ERROR MUST be ERROR level. No stuffing failure info into INFO
lines — `grep level=error` MUST catch every failure in one pass.

## Scene-specific mandatory log points

The verifier samples worker output against these lists. A missing
point fails the run.

### Robot real-hardware

Log every:

- TCP/UDP handshake (success + fail)
- Control command ACK or timeout
- Sensor data stale (>N ms no fresh sample)
- Kinematic limit triggered (joint angle / velocity limit)
- Heartbeat lost (>N missed)
- Emergency stop asserted
- Battery low threshold crossed

### Frontend ↔ Backend

Log every:

- HTTP 4xx/5xx response (always, with status + body digest)
- Auth/token validation fail
- Schema validation fail at boundary
- Long-lived connection close (websocket/SSE; expected vs unexpected)
- CORS rejection
- Request timeout (frontend)

### Cloud / distributed

Log every:

- RPC timeout / retry budget exhausted
- Rate limit (429) hit
- Degraded path triggered (fallback / cache)
- TLS cert CN/SAN mismatch
- Queue dead-letter publish
- Circuit breaker open/close

## Error-passthrough rule (do not swallow cause)

Error objects MUST preserve original message + cause chain + stack.
`String()` / `toString()` / `str()` alone swallowing the error is
forbidden. This kills the `argo_tls.rs`-style "Tauri invoke rejection
becomes `[object Object]`" class of bug.

❌ JS:
```javascript
catch(e) { log(String(e)) }            // → "[object Object]", cause lost
```
✅ JS:
```javascript
catch(e) { log({msg: e.message, cause: e.cause, stack: e.stack}) }
```

❌ Rust:
```rust
.map_err(|e| format!("{}", e))         // discards #[source]
```
✅ Rust:
```rust
.map_err(|e| anyhow!(e).context("phase=handshake op=tls"))  // chain preserved
```

❌ Python:
```python
except Exception as e: log(str(e))     # loses __cause__
```
✅ Python:
```python
except Exception as e: log.exception("op=foo phase=err")    # stack + cause auto
```

The verifier greps source for `String(`, `format!("{}",`, `str(e)`
patterns and flags any that appear in catch/error-handling blocks
without a corresponding structured cause capture.

## First-failure principle

**This is the contract's most distinctive requirement.** When a
multi-hop call chain fails, the verifier MUST be able to identify
three distinct things from the logs alone:

### `first_failure`

The **earliest FAIL event by `(ts, attempt)` within a single
`correlation_id`**. This is the root-cause candidate. Every cascade
starts here. The verifier identifies it by:

1. `grep corr=<id>` to scope the trace.
2. Within the trace, filter to `event_kind=FAIL`.
3. Sort by `(ts ASC, attempt ASC)` — the first row is
   `first_failure`.
4. Record its `(service, caller→callee, operation, phase,
   error_class, error_message+cause)`.

**Edge case — concurrent first failures:** if two FAILs share the
same `ts` and `attempt`, the verifier uses the `caller→callee` chain
to pick the upstream one. If they are in disjoint chains (two
independent business operations that happened to fail at the same
instant), they have different `correlation_id`s and are separate
traces.

### `downstream_failures`

All FAIL events in the same `correlation_id` trace that occurred
**after** `first_failure`, ordered by `(ts, attempt)`. These are the
cascade — services that failed because the upstream call failed
(positive propagation) OR services that failed concurrently for
related reasons (negative propagation, e.g. a network partition
hitting multiple peers).

The verifier lists these with their `(service, caller→callee,
operation, phase)` tuples. A `downstream_failure`'s `caller→callee`
MUST transitively connect back to `first_failure`'s `callee` via
the call chain — otherwise the trace has a missing hop (contract
violation: propagation gap).

### `final_failure`

The FAIL event that the **entry-point service** (the service that
generated `correlation_id`, identifiable by the `corr_assigned`
STATE event or by being the `caller` that no other event lists as
`callee`) **surfaced to the user/operator/system**. This is the
externally visible failure.

- It is NOT always the same as `first_failure`. A robot command
  timeout might be `first_failure`; the gateway's
  `phase=retry_exhausted` FAIL is `final_failure` — the user sees
  "command failed after retries", not "first attempt timed out".
- It is NOT always the last FAIL by `ts`. The entry-point service
  might surface `final_failure` and then a downstream service might
  log a late FAIL when its own retry budget exhausts.
- The verifier identifies it as: the FAIL event whose `service` is
  the entry-point service AND whose `phase` is `response` or
  `retry_exhausted` (i.e. the entry-point is responding to its
  caller, not making a downstream call).

### Why all three matter

- `first_failure` tells you **where to fix**. The cascade is
  downstream noise; the root cause is at the first failure.
- `downstream_failures` tells you **how far the damage spread**.
  Blast-radius analysis depends on this.
- `final_failure` tells you **what the user/system saw**. Without
  it, you cannot map logs back to operator reports or bug tickets.

### Verifier reconstruction contract

Given the logs of one `run_id`, the verifier MUST be able to produce
a table with one row per `correlation_id`:

| correlation_id | first_failure (service, op, phase, error_class) | downstream_failures count | final_failure (service, op, phase) |
|---|---|---|---|

If any column is empty for a trace that contains at least one FAIL,
the contract is violated. Empty `first_failure` while FAILs exist
means the worker logged FAILs without `correlation_id` propagation
(silent trace break). Empty `final_failure` while FAILs exist in
the entry-point service means the worker swallowed the failure
(silent user-visible failure).

## Worked example

See [`evidence.md`](evidence.md) for the 12-line log sequence
showing a real `Frontend → Gateway → Backend → Cloud → Robot`
cascade with RPC timeout → retry → retry exhausted, and the
verifier's 10-question reconstruction table.
