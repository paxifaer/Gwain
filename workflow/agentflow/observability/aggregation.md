# Aggregation — Per-Run Evidence Organization

**Component:** 汇聚 / Aggregation — how logs from multiple services
in one integration test run are laid out so the verifier can replay
the trace by greping.

This contract is agnostic about log shipping backends (Loki/Fluentd/
Vector/OTel). The verifier works against the **raw log capture** of
each service in the run. This document specifies the minimum layout
the test harness MUST produce so the verifier's grep is unambiguous.

## Per-run directory layout

The integration test harness creates one directory per `run_id`:

```
<run-root>/<run_id>/
├── meta.yaml              # run metadata: launched services, env, start/end ts
├── frontend.log           # one file per service instance
├── gateway.log
├── backend.log
├── cloud.log
├── robot-<device_id>.log   # robot logs include device_id in filename
├── stderr/                # separate capture for services that log to stderr
│   ├── frontend.stderr
│   └── ...
└── verifier/              # the verifier worker writes its reconstruction here
    ├── first-failures.csv
    ├── downstream-failures.csv
    ├── final-failures.csv
    └── reconstruction.md
```

### Why one file per service instance

The verifier greps `service=<name>` to scope a single service's
events. Putting all services' logs in one file makes the grep
return cross-service noise. One file per service means `grep
service=frontend frontend.log` returns only frontend events — the
`service` field then acts as a sanity check, not a filter.

### Why robot logs include `device_id` in the filename

`robot-SP000056.log` vs `robot-SP000033.log`. When a test run hits
multiple robots (fleet tests), the verifier needs to disambiguate
without relying on `peer_addr` (which is supplementary, see
[`context.md`](context.md)). The filename embeds the stable robot
identity.

### `meta.yaml` — run metadata

```yaml
run_id: run-20260818-001
started_at: 2026-08-18T10:00:00.000Z
ended_at: 2026-08-18T10:05:42.381Z
env:
  GAWAIN_RUN_ID: run-20260818-001
services:
  - name: frontend
    instance_id: fe-pod-7f4c
    log: frontend.log
    transport_in: HTTP  # what it receives from
    transport_out: HTTP  # what it calls out with
  - name: gateway
    instance_id: gw-pod-2a1b
    log: gateway.log
    transport_in: HTTP
    transport_out: gRPC
  - name: robot-ctrl
    instance_id: SP000056
    device_id: SP000056
    log: robot-SP000056.log
    transport_in: zenoh
    transport_out: zenoh
acceptance:
  spec: handoffs/<task>/SPEC.md
  criteria:
    - "robot executes cmd within 200ms ack"
    - "no FAIL events with phase=timeout in the entry service"
```

The verifier reads `meta.yaml` first to learn what services
participated, then greps each `*.log` in scope.

## Per-service log capture

Each service writes logs to its own file. The test harness
captures three streams:

1. **Structured log output** — the worker's `tracing`/`logging`
   output, redirected to `<service>.log`. This is the primary
   evidence.
2. **stderr** — anything the process wrote to stderr (panics,
   uncaught exceptions, library debug output). Captured to
   `stderr/<service>.stderr`. The verifier greps this for
   panics and stack traces that bypassed the structured logger.
3. **Exit code + signal** — recorded in `meta.yaml`'s service
   entry. A service that crashed with SIGKILL has no final log
   line; the verifier needs the exit code to know it died.

### What if a service logs to stdout?

If the worker's logging library is configured for stdout (common
in containerized services), the test harness redirects stdout to
`<service>.log`. The same field-form rules apply (see
[`context.md`](context.md)) — the verifier greps field names,
not JSON paths, so stdout logs are fine as long as the fields are
present.

### What if a service is containerized?

For k8s: `kubectl logs -n <ns> <pod>` redirected to
`<service>.log`. For docker: `docker logs <container>` redirected.
The harness MUST capture logs before terminating the container
(post-run capture loses logs if the container is deleted).

### What if a service is on a remote robot?

SSH to the robot, capture the log file (or `journalctl -u
<service>` if systemd-managed). Copy back to the per-run
directory as `robot-<device_id>.log`. The test harness is
responsible for this; the worker code is not.

## What the verifier greps

Given the per-run directory, the verifier runs these greps:

1. **Scope to the run:** `grep run_id=<run_id>` across all
   `*.log` files. Any line without `run_id=<run_id>` in a service
   that participated is either a misconfigured service (logged
   `run_id=prod`) or a leftover from a prior run (log rotation
   failure). Both are flagged.
2. **Scope to a trace:** `grep corr=<correlation_id>` across all
   `*.log` files. Returns the full event sequence for that
   business operation.
3. **Find first_failure:** within the trace scope, `grep
   event_kind=FAIL`, sort by `(ts, attempt)`, take the first.
4. **Find downstream_failures:** same grep, all rows after
   `first_failure`.
5. **Find final_failure:** within the trace scope, `grep
   service=<entry-service> phase=retry_exhausted` OR `service=
   <entry-service> phase=response` — the entry service's
   response to its caller.
6. **Check cause preservation:** `grep -E 'String\(|format!\("\{\}",
   ' <service>.rs` in the worker's source (separate from logs).

## Cross-service ordering

Cross-machine clock skew is expected (see [`context.md`](context.md)).
The verifier reconstructs order using `ts` AND `attempt` + the
`caller→callee` chain. When the verifier reports a trace, it
shows:

```
[1] ts=2026-08-18T10:00:00.001Z corr=corr-7f3a9c attempt=1 \
    service=frontend event_kind=STATE from_state=idle to_state=in_progress
[2] ts=2026-08-18T10:00:00.020Z corr=corr-7f3a9c attempt=1 \
    service=frontend caller=frontend callee=gateway phase=request
[3] ts=2026-08-18T10:00:00.095Z corr=corr-7f3a9c attempt=1 \
    service=gateway  caller=gateway  callee=backend  phase=request
...
```

The `[1]`, `[2]`, `[3]` ordering is the verifier's reconstruction,
not the raw `ts` order — if `[3]`'s `ts` is earlier than `[2]`'s
due to clock skew, the verifier uses the `caller→callee` chain to
put `[3]` after `[2]`.

## Retention

- **Integration test runs:** retain the per-run directory for the
  duration of the task's acceptance cycle. The orchestrator decides
  when to clean up (typically after the verifier accepts, or after
  the user signs off).
- **Production logs:** out of scope. This contract does not specify
  production retention; production is governed by the deployment's
  own log policy.

## What this aggregation deliberately does NOT provide

- No log shipper requirement. The harness captures raw files.
- No central aggregation service. The verifier greps files in
  the per-run directory.
- No schema migration tooling. Field names are stable (see
  [`context.md`](context.md)); adding a field is additive.
- No real-time tailing. The verifier runs post-hoc, after the
  test run completes. (Real-time tailing is a P1 concern; the
  field set here would support it, but it's not required.)
