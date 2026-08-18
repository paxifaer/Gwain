# Context — Identity Model and Common Fields

**Component:** 上下文 / Context — the stable identity that every event carries.

The verifier reconstructs a multi-machine call chain by greping for
identity fields. Identity is **logical**, not physical. IP addresses
are **never** identity — they shift across reboots, NAT, DHCP, and
container restarts; using them as the primary key breaks trace
reconstruction.

## The 8 common fields (required for ALL events — FAIL/ERROR/STATE)

Every log line — FAIL, ERROR, or STATE — MUST contain these fields:

| # | field | meaning | example |
|---|-------|---------|---------|
| 1 | `ts` | ISO8601 UTC ms-precision; logging library must emit on every line; do NOT disable | `2026-08-18T10:00:00.001Z` |
| 2 | `level` | `ERROR` \| `INFO` \| `DEBUG` | `ERROR` |
| 3 | `event_kind` | `FAIL` \| `ERROR` \| `STATE` | `FAIL` |
| 4 | `run_id` | one per integration test run; propagate via env `GAWAIN_RUN_ID`; production fallback `prod` or deployment id | `run-20260818-001` |
| 5 | `correlation_id` | one per business operation; propagate across all hops (see [`propagation.md`](propagation.md)) | `corr-7f3a9c` |
| 6 | `attempt` | 1-indexed retry counter, default `1` (no retry) | `2` |
| 7 | `service` | logical name of WHO logs (not IP) | `frontend`, `auth-svc`, `robot-ctrl` |
| 8 | `instance_id` | process/container id of WHO logs | `fe-pod-7f4c`, `hostname+pid12345` |

### Why these are non-negotiable

- Without `run_id`, you cannot tell which integration test run a log
  line came from — cross-run contamination makes the verifier's grep
  return false matches.
- Without `correlation_id`, you cannot chain hops into a trace — a
  FAIL at the robot end is indistinguishable from a FAIL at the cloud
  end for the same user action.
- Without `attempt`, you cannot tell whether a FAIL is the first try
  or a retry — retry-exhausted FAILs need different triage than
  first-attempt FAILs.
- Without `service` + `instance_id`, you cannot tell WHO logged — the
  same hostname can run multiple services (gateway + admin on one
  box), and the same service can run multiple instances behind a
  load balancer.

### Stable identity vs supplementary address

- `service` (logical name) — **stable identity**. e.g. `auth-svc`,
  `robot-ctrl`, `frontend`. Never an IP.
- `instance_id` (process/container id) — **stable within a process
  lifetime**. e.g. `fe-pod-7f4c`, `hostname+pid12345`. Never an IP.
- `device_id` (robot fleet id) — **stable across robot lifetime**.
  e.g. `SP000056`. Mandatory on robot scene; optional elsewhere.
  See [`events.md`](events.md) for scene-specific rules.
- `peer_addr` (physical address) — **supplementary only**. e.g.
  `10.0.0.2:443`. Appears in FAIL-specific fields (see
  [`events.md`](events.md)) for network-level debugging. NEVER used
  as the primary key for trace reconstruction.

**Iron rule:** `grep service=auth-svc instance_id=fe-pod-7f4c` MUST
return all events that this specific process emitted, regardless of
which IP it was reachable on at the time. If `peer_addr` is the only
way to find an event, the contract is broken.

## Field form

Field form is your choice. JSON serialization is NOT required. The
verifier greps field NAMES, not JSON paths, so any of these is
acceptable:

**Structured fields (Rust tracing):**
```rust
tracing::error!(
    caller = "frontend",
    callee = "gateway",
    op = "POST /api/cmd",
    phase = "timeout",
    error_class = "Timeout",
    error_message = %e,
    cause = ?e.source(),
    "cross-boundary call failed"
);
```

**Text key=value (any language):**
```text
level=error event_kind=FAIL ts=2026-08-18T10:00:08.025Z \
  run_id=run-20260818-001 corr=corr-7f3a9c attempt=1 \
  service=frontend instance_id=fe-pod-7f4c \
  caller=frontend callee=gateway op="POST /api/cmd" \
  phase=timeout peer_addr=10.0.0.2:443 \
  latency_ms=5000 error_class=Timeout \
  error_message="timeout 5000ms" cause="peer not responding"
```

**Python structured logging:**
```python
logger.error("cross-boundary call failed",
    extra={"event_kind": "FAIL", "caller": "frontend",
           "callee": "gateway", "op": "POST /api/cmd",
           "phase": "timeout", "error_class": "Timeout",
           "error_message": str(e), "cause": str(e.__cause__)})
```

**JS structured args:**
```javascript
log.error({event_kind: "FAIL", caller: "frontend",
           callee: "gateway", op: "POST /api/cmd",
           phase: "timeout", error_class: "Timeout",
           error_message: e.message, cause: e.cause,
           stack: e.stack},
          "cross-boundary call failed");
```

The rule: `grep <field_name>=` must find the field in every event
that should carry it.

## Cross-machine clock skew

Cross-machine clock skew is expected. The verifier reconstructs
order within a trace using `ts` AND `attempt` + `caller→callee`
sequence (not `ts` alone). When two events have `ts` within
clock-skew tolerance and disagree on order, `attempt` and the
`caller→callee` chain are authoritative.

## Why no new infrastructure

This contract deliberately uses only the logging library the worker's
language already has. There is:

- No OpenTelemetry SDK requirement (OTel is allowed if the project
  already uses it; not mandated).
- No log shipper requirement (Loki/Fluentd/Vector are allowed if the
  project already uses them; not mandated).
- No schema registry. Field names are greppable strings.
- No central aggregation service. The verifier greps the raw log
  files / pod logs / captured stdout of each service in the run.

The contract's value comes from the **fields** being present on every
event, not from any aggregation backend. A future task may add a
collector; this contract does not require it.
