# Evidence — 8 Verifier Checks, Bypass Vectors, and Worked Example

**Component:** 证据 / Evidence — the adversarial checklist the
verifier worker runs against the worker's code + the captured logs.

This file is the verifier's primary reference. It lists the 8
traceability checks, the **bypass vector** a strong worker agent
might use to fake compliance, and the **verifier countermeasure**
that catches the bypass. Then it shows a 12-line worked example
and the 10-question reconstruction table the verifier must produce.

## 8 verifier checks

### Check 1 — Log presence

**Pass:** every scene-specific mandatory log point listed in
[`events.md`](events.md) appears in the captured logs with a real
`file:line` reported by the worker.

**Bypass vector:** the worker logs nothing at all, then in its
final message reports "all log points implemented at file:line
X:Y" with fabricated line numbers.

**Verifier countermeasure:**
- Grep the captured `*.log` for each mandatory point. If the grep
  returns zero rows for a point the worker claimed, the worker
  fabricated it.
- Cross-reference the worker's reported `file:line` against the
  actual source — read the source at that line and confirm the
  logging call exists. A line number pointing at a comment or an
  unrelated function is fabrication.

### Check 2 — Correlation correctness

**Pass:** every event in the trace has `correlation_id`. If
inbound had none, a `from_state=no_corr to_state=corr_assigned`
STATE event exists for that trace.

**Bypass vector:** the worker logs FAIL events without
`correlation_id` ("we don't propagate correlation_id in this
service, it's internal"), hoping the verifier only checks entry
and exit points.

**Verifier countermeasure:**
- `grep event_kind=FAIL` returns FAILs; for each, check the same
  log line has `corr=<id>`. Any FAIL without `corr` is a violation.
- `grep event_kind=ERROR` same check.
- `grep event_kind=STATE` same check (with the documented
  exception of the very first entry-point assignment STATE).
- For services that handle inbound HTTP (gateway, backend), grep
  for `corr_assigned` STATE events — if the service ever receives
  an inbound request without `correlation_id`, it MUST have logged
  the assignment. Absence of `corr_assigned` while the service
  also has FAILs without `corr` indicates silent dropping.

### Check 3 — Identity correctness

**Pass:** events use `service` + `instance_id` (+ `device_id` on
robot scene) as stable identity. `peer_addr` is supplementary
only. IP is NEVER identity.

**Bypass vector:** the worker uses `peer_addr` as the primary
key, with `service` either absent or set to the IP string ("we
identified the robot by its IP, what's the problem?").

**Verifier countermeasure:**
- For every event, check `service=<logical-name>` matches
  `^[a-z][a-z0-9-]+$` (lowercase logical name, not an IP). A
  `service` field matching `^\d+\.\d+\.\d+\.\d+$` is a violation.
- Check `instance_id` is present and not an IP.
- On robot scene, check `device_id` is present on every FAIL event.
- Check `peer_addr` only appears in FAIL events (it's
  FAIL-specific, see [`events.md`](events.md)). If `peer_addr`
  appears in ERROR or STATE events, the worker is using it as
  primary identity — violation.
- The acid test: pick any event in the trace, then `grep
  service=<service> instance_id=<instance_id>`. This MUST return
  all events from that process, regardless of what IP it was on.
  If the only way to find the event is `peer_addr=<ip>`, the
  contract is broken.

### Check 4 — Failure semantics

**Pass:** every FAIL event has `caller→callee`, `operation`,
`phase`, `error_class`, `error_message+cause`. Every
retry-budget exhaustion emits a FAIL with
`phase=retry_exhausted`.

**Bypass vector:** the worker logs FAILs with `error_message`
but no `error_class` or `cause` ("we don't classify errors in
this service"), and lets the retry budget exhaust silently.

**Verifier countermeasure:**
- For every `event_kind=FAIL` row, check `caller=` AND `callee=`
  AND `op=` AND `phase=` AND `error_class=` AND `error_message=`
  AND `cause=` all appear on the same log line.
- For every trace (`corr=<id>`) that has at least one
  `phase=retry` or `phase=timeout` FAIL, check there is also a
  `phase=retry_exhausted` FAIL OR a successful response. A trace
  with retries but no `retry_exhausted` and no success means the
  worker gave up silently.
- `phase` must be one of the enum values in [`events.md`](events.md)
  (`request` / `response` / `handshake` / `timeout` / `retry` /
  `retry_exhausted`). Anything else is a typo or a custom value
  the contract doesn't recognize — violation.

### Check 5 — Retry semantics

**Pass:** `attempt` is 1-indexed, propagates across hops,
downstream services do NOT increment it.

**Bypass vector:** each service along the chain increments
`attempt` ("we retry internally too, so we incremented") —
the verifier can't tell whether `attempt=3` means entry retried
3 times or the call went 3 hops deep.

**Verifier countermeasure:**
- For a given `corr=<id>`, the `attempt` values at the entry
  service should form a contiguous sequence `1, 2, 3, ..., N`
  (or just `1` if no retries).
- Downstream services should log the SAME `attempt` value as
  the entry service's current attempt. If the entry service is
  on `attempt=2` and the downstream logs `attempt=3`, the
  downstream incremented — violation.
- The check: pick a `(corr, attempt)` pair at the entry service,
  then grep downstream services for the same `corr` — their
  `attempt` MUST match the entry's value, not exceed it.

### Check 6 — Cause preservation

**Pass:** no `String(error)` / `format!("{}", e)` / `str(e)`
patterns in source that swallow the cause chain. Every error
chain preserves `cause` + stack.

**Bypass vector:** the worker writes `catch(e) { log(String(e)) }`
in JS, or `.map_err(|e| format!("{}", e))` in Rust, and reports
"all error handling preserves cause" — the verifier can't tell
from the logs alone that the cause was dropped.

**Verifier countermeasure:**
- Grep the worker's source for the banned patterns:
  - JS: `catch\s*\([^)]*\)\s*\{[^}]*String\s*\(` (String() in
    catch blocks)
  - Rust: `format!\s*\("\{\}"\s*,` (format!("{}", ...)) and
    `\.map_err\s*\(\|[^|]*\|\s*format!`
  - Python: `except\s+[^:]+:\s*\n\s*.*str\s*\(\s*e\s*\)` (str(e)
    in except blocks)
- For each match, read the surrounding context (5 lines). If the
  match is in a catch/error block AND the same block does not
  also log `e.cause` / `e.source()` / `e.__cause__` / `e.stack`,
  it's a violation.
- For each FAIL log line, check `cause=` appears. Absence of
  `cause=` on a FAIL that originated from a caught error is a
  violation.

### Check 7 — First-failure reconstruction

**Pass:** the verifier can identify `first_failure`,
`downstream_failures`, and `final_failure` for every trace that
contains at least one FAIL. See [`events.md §first-failure`](events.md)
for the definitions.

**Bypass vector:** the worker logs FAILs across multiple services
without `correlation_id` propagation, so each service's FAILs are
isolated — the verifier can't tell which is the cascade root.

**Verifier countermeasure:**
- For each `corr=<id>` trace containing FAILs, sort by
  `(ts, attempt)` and take the first as `first_failure`. Record
  its `(service, caller→callee, operation, phase, error_class)`.
- List all subsequent FAILs in the trace as `downstream_failures`.
  Verify each `downstream_failure`'s `caller→callee` transitively
  connects back to `first_failure`'s `callee` — a gap means a
  service in the middle dropped `correlation_id` (propagation
  violation, also caught by Check 2).
- Identify the entry-point service for the trace (the service
  that generated `correlation_id` — either the one with the
  `corr_assigned` STATE event OR the one that no other event
  lists as `callee`). Within that service's FAILs in this trace,
  the `phase=response` or `phase=retry_exhausted` FAIL is
  `final_failure`.
- Build the table:

| correlation_id | first_failure (svc, op, phase, err_class) | downstream_failures count | final_failure (svc, op, phase) |
|---|---|---|---|

- Any row with an empty cell (while the trace has FAILs) is a
  violation:
  - Empty `first_failure` → FAILs without `correlation_id`
    (Check 2 violation).
  - Empty `final_failure` → entry service swallowed the failure
    (no `phase=response` or `phase=retry_exhausted` FAIL at the
    entry service while downstream FAILs exist — Check 4
    violation).
  - Empty `downstream_failures` is fine (single-hop failure,
    no cascade).

### Check 8 — Scope completeness

**Pass:** all services in the run share `run_id` from env
`GAWAIN_RUN_ID`. No service logged `run_id=prod` during an
integration test run.

**Bypass vector:** a service wasn't wired to the test harness, so
it reads `GAWAIN_RUN_ID` as unset and logs `run_id=prod`. The
worker reports "all services log run_id" — technically true, but
the values disagree.

**Verifier countermeasure:**
- Read `meta.yaml` (see [`aggregation.md`](aggregation.md)) for
  the list of services in the run and the expected `run_id`.
- For each `*.log` file, `grep run_id=` and check every row has
  the expected `run_id=<run_id>`.
- Any row with `run_id=prod` in a service that participated in
  the test run is a misconfiguration — the service wasn't wired
  to `GAWAIN_RUN_ID`.
- Any row with a different `run_id=<value>` (not `prod`, not the
  expected) is a leftover from a prior run (log rotation failure)
  — violation.

## Worked example — 12-line cascade

Scenario: User clicks "send command" in the frontend. The
command flows Frontend → Gateway → Backend → Cloud → Robot.
The robot's zenoh session is dead. The cloud's RPC to the robot
times out at 8000ms. The cloud retries twice (within its retry
budget of 3 attempts). All attempts fail. The cloud surfaces
`phase=retry_exhausted` to the backend. The backend surfaces the
FAIL to the gateway. The gateway surfaces the FAIL to the
frontend. The frontend logs `final_failure`.

```
[1]  ts=2026-08-18T10:00:00.001Z level=INFO  event_kind=STATE service=frontend instance_id=fe-pod-7f4c run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=idle to_state=in_progress reason=button_click
[2]  ts=2026-08-18T10:00:00.020Z level=DEBUG event_kind=STATE service=frontend instance_id=fe-pod-7f4c run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=in_progress to_state=waiting_gateway reason=invoke
[3]  ts=2026-08-18T10:00:00.095Z level=DEBUG event_kind=STATE service=gateway  instance_id=gw-pod-2a1b run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=idle to_state=in_progress reason=inbound_http
[4]  ts=2026-08-18T10:00:00.140Z level=DEBUG event_kind=STATE service=backend  instance_id=be-pod-9c2d run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=idle to_state=in_progress reason=inbound_grpc
[5]  ts=2026-08-18T10:00:00.190Z level=DEBUG event_kind=STATE service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=idle to_state=in_progress reason=inbound_grpc
[6]  ts=2026-08-18T10:00:08.025Z level=ERROR event_kind=FAIL service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 caller=cloud callee=robot op="zenoh pub cmd/vel" phase=timeout peer_addr=192.168.110.56:7447 device_id=SP000056 latency_ms=8000 error_class=Timeout error_message="zenoh query timeout 8000ms" cause="peer not responding"
[7]  ts=2026-08-18T10:00:08.041Z level=INFO  event_kind=STATE service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 from_state=in_progress to_state=retrying reason=attempt_1_failed
[8]  ts=2026-08-18T10:00:16.030Z level=ERROR event_kind=FAIL service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=2 caller=cloud callee=robot op="zenoh pub cmd/vel" phase=timeout peer_addr=192.168.110.56:7447 device_id=SP000056 latency_ms=8000 error_class=Timeout error_message="zenoh query timeout 8000ms" cause="peer not responding"
[9]  ts=2026-08-18T10:00:16.046Z level=INFO  event_kind=STATE service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=2 from_state=retrying to_state=retrying reason=attempt_2_failed
[10] ts=2026-08-18T10:00:24.031Z level=ERROR event_kind=FAIL service=cloud    instance_id=cloud-1a4b run_id=run-20260818-001 corr=corr-7f3a9c attempt=3 caller=cloud callee=robot op="zenoh pub cmd/vel" phase=timeout peer_addr=192.168.110.56:7447 device_id=SP000056 latency_ms=8000 error_class=Timeout error_message="zenoh query timeout 8000ms" cause="peer not responding"
[11] ts=2026-08-18T10:00:24.047Z level=ERROR event_kind=FAIL service=cloud    instance_id=cloud-1a4b run_id=run-60818-001 corr=corr-7f3a9c attempt=3 caller=cloud callee=robot op="zenoh pub cmd/vel" phase=retry_exhausted peer_addr=192.168.110.56:7447 device_id=SP000056 latency_ms=24000 error_class=RetryExhausted error_message="retry budget 3 exhausted" cause="3 consecutive timeouts"
[12] ts=2026-08-18T10:00:24.080Z level=ERROR event_kind=FAIL service=frontend instance_id=fe-pod-7f4c run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 caller=gateway callee=frontend op="HTTP 500 /api/cmd" phase=response peer_addr=gw-pod-2a1b latency_ms=24080 error_class=UpstreamTimeout error_message="gateway returned 500" cause="cloud retry exhausted on robot cmd"
```

(Note: line [11] has a typo `run-60818-001` to illustrate Check 8
catching a misconfigured service — in a real pass, all rows share
the exact `run_id`.)

## 10-question reconstruction table

Given only the captured `*.log` files and `meta.yaml` for this
run, the verifier answers these 10 questions. Each row shows the
question, the grep that answers it, and the answer from the
worked example.

| # | Question | Grep | Answer from example |
|---|---|---|---|
| 1 | Which run did this trace belong to? | `grep corr=corr-7f3a9c` → read `run_id` field | `run-20260818-001` |
| 2 | Which business operation (entry trigger)? | `grep corr=corr-7f3a9c event_kind=STATE` → first row's `reason` | `button_click` at frontend |
| 3 | Which services participated? | unique `service=` values in `corr=corr-7f3a9c` rows | `frontend, gateway, backend, cloud, robot-ctrl (callee only — robot has no log rows because it was unreachable)` |
| 4 | Which was the FIRST failure? | `grep corr=corr-7f3a9c event_kind=FAIL` → sort by `(ts, attempt)` → first row | row [6]: cloud→robot zenoh pub, `phase=timeout`, `error_class=Timeout`, 8000ms |
| 5 | Was this a retry? | `attempt` field on row [6] | `attempt=1` — no, first attempt |
| 6 | How many retries happened? | max `attempt` value in `corr=corr-7f3a9c event_kind=FAIL` rows | 3 attempts (attempt=1, 2, 3) |
| 7 | Was retry budget exhausted? | `grep corr=corr-7f3a9c phase=retry_exhausted` | yes — row [11], `phase=retry_exhausted` |
| 8 | What was the full cause chain? | `cause=` field across the trace | "peer not responding" → "3 consecutive timeouts" → "cloud retry exhausted on robot cmd" |
| 9 | What was the FINAL failure (user-visible)? | entry-service FAIL with `phase=response` or `phase=retry_exhausted` | row [12]: frontend's `phase=response` FAIL, `error_class=UpstreamTimeout`, "gateway returned 500" |
| 10 | What was the blast radius (downstream_failures)? | all FAILs in trace after `first_failure` | rows [8], [10], [11], [12] — cloud retries 2 and 3, cloud's retry_exhausted, frontend's response FAIL |

## Final-message report — what the worker must list

In its final message, the worker MUST list every FAIL/ERROR/STATE
log point it implemented, with `file:line` for each. The verifier
samples this against:

- the scene-specific mandatory list in [`events.md`](events.md)
- the common-field checklist in [`context.md`](context.md)
- the propagation implementation in [`propagation.md`](propagation.md)
  (HTTP header / RPC metadata / zenoh user properties / Tauri
  invoke arg / WebSocket first message / IPC message header —
  whichever applies to the worker's code)
- the timestamp format (ISO8601 UTC ms-precision, see
  [`context.md`](context.md))
- the `phase=retry_exhausted` usage on retry-budget-exhausted FAILs
  (see [`events.md`](events.md))

A missing point or field fails the run.
