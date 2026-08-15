# Sync Protocol — Discussion ↔ Orchestrator

status: normative. This file is the source of truth for the *shape* of the protocol. Workers, prompts, and the orchestrator all cite this file. If a prompt file ever disagrees with this file, this file wins.

source of authority: `workflow/handoffs/discussion-sync/SPEC-discussion-sync.md` (user-approved 2026-08-14).

---

## Scope & Non-goals

(copied verbatim from SPEC §2)

- ❌ No MCP server / database / runtime service / network calls / new CLI binaries
- ❌ No migration of existing tasks under `workflow/handoffs/*` (argodds-tools, skyline-network-config, demoapp-network-config, argoclient-cloud-off, platform-merge-dev, ci-container stay as-is)
- ❌ **Not a mandatory precondition for new tasks.** A task opts in by creating the new layout; otherwise it keeps using the old SPEC-*.md convention.
- ❌ No rewrites of any existing `workflow.md` section (Dispatch Mindset, Prompt Design, Dispatch Loop, Output Contract, Verification, Escalate, Red Flags, Failure Modes, Model Selection). Append-only.
- ❌ No git commits, no pushes. Orchestrator reviews after workers finish.
- ❌ No new Python/Go/Rust/shell code. Protocol is carried by markdown docs + yaml payload template + prompt templates.

---

## Vocabulary

- **Discussion Session** — a Claude Code conversation in which the human and assistant explore options, propose choices, and confirm or reject ideas. Source of `/sync`. Never mutates ledger files.
- **Orchestrator Session** — a Claude Code conversation that plans, dispatches workers, judges results, and (under this protocol) ingests sync payloads. Mutates ledger files via ingest.
- **Task Ledger** (or *ledger*) — the union of `<task>/task.md`, `<task>/decisions.md`, `<task>/state.md`, and all `<task>/sync/*.yaml` regardless of `status:`. The authoritative record of task state.
- **Item** — a single structured record inside the ledger or a sync payload: a Requirement, Decision, Constraint, Progress entry, Open Question, or Rejected alternative. Every item has an ID.
- **Sync Payload** — a single YAML file `<task>/sync/NNN.yaml` carrying a batch of new or revised items produced by one `/sync` invocation. Status starts `pending`.
- **Item ID** — a per-task monotonically increasing identifier of the form `<prefix>-<NNN>` (see §ID Conventions). The proposed ID is set by the extractor; ingest is authoritative and may renumber on MERGE.
- **Ingest** — the Orchestrator-side operation that reads pending sync payloads, assigns each entry a disposition (ACCEPT/MERGE/REJECT/CONFLICT), mutates the ledger accordingly, and rewrites the payload's `status:`.
- **Entry Class** — one of `CONFIRMED`, `PROPOSED`, `EXPLORATORY`, `IRRELEVANT`, carried per-entry inside `changes.{requirements,decisions,constraints}`. Determines whether the entry is eligible for transcription into the ledger.
- **Disposition** — the per-entry verdict assigned by ingest. Exactly one of `ACCEPT`, `MERGE`, `REJECT`, `CONFLICT` (see §Entry Classes & Dispositions).

---

## Allowed Categories

(copied verbatim from SPEC §6.1)

The only things that may appear in `changes:`:

- `requirements`
- `decisions`
- `constraints`
- `progress`
- `open_questions`
- `rejected`

One sentence per category, with example:

- **`requirements`** — a thing the task must satisfy, written into `task.md § Requirements` when CONFIRMED. Example: "R-003 — the gateway MUST retry on 5xx with exponential backoff — user-stated constraint from 2026-08-14".
- **`decisions`** — a committed choice between alternatives, written into `decisions.md § Decisions` when CONFIRMED. Example: "D-002 — use TLS not mTLS, cert lifecycle is simpler — confirmed 2026-08-14".
- **`constraints`** — an inviolable boundary the task must respect, written into `decisions.md § Constraints` when CONFIRMED. Example: "C-001 — must not introduce new Python dependencies — repo policy".
- **`progress`** — a fact about work done, written into `state.md § Completed` (or `§ In Progress` if `next_action` references it). Example: "P-004 — gateway retry path implemented, tests green — evidence: tests/gateway_retry_test.go".
- **`open_questions`** — an unresolved question the human wants tracked, written into `state.md § Open Questions`. Example: "Q-002 — do we need mTLS for intra-cluster traffic, or is TLS enough?".
- **`rejected`** — an alternative the human explicitly rejected, written into `decisions.md § Rejected`. Example: "X-001 — mTLS — cert lifecycle too heavy for our operational budget — rejected 2026-08-14".

---

## Forbidden Categories

(copied verbatim from SPEC §6.2)

The following must never appear in a sync payload:

- Chitchat / social / unrelated topics
- Open questions asked purely for exploration
- Discarded alternatives (unless reaching `rejected` status with a reason)
- Duplicates of already-recorded IDs
- Speculative guesses not yet CONFIRMED
- Anything not relevant to the current task

| Example of forbidden | What to do instead |
|---|---|
| "we talked about the weather, then lunch" | emit nothing; this is chitchat, not task-relevant |
| "should we consider QUIC? not sure yet, need benchmarks" *as uncommitted musing* | classify `IRRELEVANT` per SPEC §14 A-1 → emit **no payload entry**. `open_questions` (Q-XXX) is reserved for genuine blocking questions (e.g., "what cert overlap period should we use?"), never for exploratory musing |
| "we considered Rust but dropped it" *without a reason* | do not emit; a rejected alternative needs a reason to be recorded as `rejected`. Either re-discuss and reach a documented rejection, or omit. |
| a new entry with the same ID as an existing ledger entry, but different content | do not re-use the ID. Use `revises: <old-ID>` on a new ID to revise; or, if the content is genuinely new, pick the next free ID. |

---

## Entry Classes & Dispositions

### Entry Classes (SPEC §6.3 verbatim)

Every entry in `changes.{requirements,decisions,constraints}` MUST carry a `class` field:

| class | meaning | ingest effect |
|---|---|---|
| `CONFIRMED` | user explicitly confirmed in Discussion | eligible to be written to `task.md` / `decisions.md` |
| `PROPOSED` | one option the human leans toward but did NOT confirm | carried in payload; NOT written to decisions.md |
| `EXPLORATORY` | pure exploration, no commitment | carried in payload; NOT written to decisions.md; state.md `open_questions` may reference |
| `IRRELEVANT` | not task-relevant | MUST NOT appear in payload at all |

`progress`, `open_questions`, `rejected` entries do NOT carry `class` (they are inherently factual records or explicit pans).

### Dispositions (SPEC §6.8 verbatim)

For each entry inside a pending sync payload, the Orchestrator's ingest prompt assigns exactly one:

- `ACCEPT` — entry transcribed into the ledger (`task.md` or `decisions.md` or `state.md`)
- `MERGE` — entry revises an existing entry (with `revises: <ID>`); old line kept but annotated
- `REJECT` — entry discarded; reason recorded in the sync file's `status_notes`
- `CONFLICT` — entry semantically contradicts an already-applied ledger entry on the same subject; ingest flips payload `status: conflict`, does NOT overwrite the ledger, surfaces to human

---

## ID Conventions

(copied verbatim from SPEC §6.4)

- `D-001, D-002, ...` — decisions, monotonically increasing per task
- `C-001, C-002, ...` — constraints
- `R-001, R-002, ...` — requirements
- `P-001, P-002, ...` — progress entries
- `Q-001, Q-002, ...` — open questions
- `X-001, X-002, ...` — rejected alternatives

The Extractor proposes IDs; the Orchestrator's ingest is authoritative (may renumber on merge and explain).

---

## Ordering & Versioning within a task

Sync payloads are written as `<task>/sync/001.yaml`, `<task>/sync/002.yaml`, …, zero-padded to three digits on disk. The `sync_id:` field inside the file is an integer (`1`, `2`, …) that matches the filename.

Ingest processes `sync/*.yaml` in **ascending numeric order of `sync_id`**, never skip. If a file `NNN.yaml` is missing but `NNN+1.yaml` exists (e.g., `005.yaml` is absent but `006.yaml` is present), ingest MUST flag `missing_sync` and MUST NOT proceed past the gap. The human is responsible for restoring the missing file or renumbering. The extractor MUST compute the next `sync_id` as `max(existing_ids) + 1` and MUST NOT renumber or rewrite older files (see §Idempotency).

Files are never renamed or deleted by the protocol. Their `status:` field and the envelope bookkeeping fields (`applied_at`, `applied_by`, `status_notes`) are the only fields ingest rewrites, per SPEC §14 A-3.

---

## Incremental Sync; Ledger Not Cursor

(copied verbatim from SPEC §6.5)

Claude Code does not expose a reliable conversation checkpoint API. Therefore the sync protocol uses **ledger semantics** instead of cursor semantics:

- The extractor receives (in its prompt context) the list of all item IDs already present in `task.md`/`decisions.md`/`state.md`/applied `sync/*.yaml`.
- The extractor may ONLY emit entries that are NOT already in the ledger.
- To revise an existing entry: emit a new entry with `revises: <ID>` field and the full replacement content.
- There is no "give me everything since timestamp T" mode.

### Worked example

Suppose the ledger (union of `task.md`, `decisions.md`, `state.md`, all applied `sync/*.yaml`) contains these IDs:

```
R-001, R-002, D-001, D-002, C-001, P-001, Q-001, X-001
```

**Ledger-consistent extractor output (valid):**

```yaml
# 005.yaml
sync_id: 5
task_id: example-task-001
source: discussion
created_at: 2026-08-14T20:30:00Z
status: pending
changes:
  decisions:
    - id: D-003               # next free decision ID; ledger had D-001, D-002
      class: CONFIRMED
      content: "Use TLS over mTLS, cert lifecycle is simpler."
      reason: "User confirmed 2026-08-14."
      revises: null
  open_questions:
    - id: Q-002               # next free question ID; ledger had Q-001
      content: "Do we need to rotate certs out-of-band, or rely on the orchestrator?"
```

This is ledger-consistent: D-003 and Q-002 are both new IDs not in the ledger.

**NOT ledger-consistent (invalid):**

```yaml
# 005.yaml
sync_id: 5
status: pending
changes:
  decisions:
    - id: D-002               # COLLISION — D-002 is already in the ledger
      class: CONFIRMED
      content: "Use mTLS over TLS."     # and semantically conflicts (see §Conflict Detection)
      revises: null                    # if it were a revision, revises: D-002 would be required
```

This payload violates the ledger rule because (a) the ID `D-002` is already in the ledger, and (b) the content is a different decision on the same subject but `revises:` is null instead of `D-002`. Ingest will mark this entry `CONFLICT` (or `REJECT` if the human considers it a duplicate), and the file's `status:` becomes `conflict`. The extractor should instead have proposed `D-003` with `revises: D-002` if the intent was to revise, or `D-003` with `revises: null` if it was an unrelated decision on a new subject.

---

## Idempotency

(copied verbatim from SPEC §6.6)

1. If the extractor finds zero new content to add, it MUST NOT write any `sync/NNN.yaml` file. It replies to the user with text like "no new task-relevant changes since last sync" and updates nothing on disk.
2. Ingest scans `sync/*.yaml` for files whose `status: pending`. After processing it rewrites the file to `status: applied | rejected | conflict`. Repeated ingest runs on a fully-applied task are no-ops by construction.
3. If running `/sync` twice in a row in Discussion produces no new content between the runs, the second run writes nothing. (Consequence of rule 1.)

### A4 scenario — `/sync` twice with no new Discussion content

The human runs `/sync` once. The Discussion has, since the last sync, produced one confirmed decision ("D-003 — use TLS over mTLS"). The extractor computes the ledger (which currently contains D-001, D-002, ...), finds D-003 is new, and writes `sync/005.yaml` with `status: pending` containing one `decisions` entry D-003. Reply to human: `Sync payload 005.yaml created. Changes: 1 decision.`

The human then runs `/sync` again *immediately*, with no further Discussion in between. The extractor recomputes the ledger — and now the ledger includes `sync/005.yaml` (regardless of its `status:`, applied or pending — see §Incremental Sync). The set of IDs in the ledger is now `..., D-003, ...`. The Discussion has no new content; the extractor finds zero new IDs to emit. Per rule 1, the extractor writes nothing and replies: `No new task-relevant changes since last sync.`

Counting files on disk: `sync/` has `005.yaml` (still `pending`, since the Orchestrator hasn't ingested yet) and nothing else new. Decisions and state on the ledger are unchanged. Ingest, when later run, will process `005.yaml` exactly once — its `status:` becomes `applied`, and subsequent ingest runs are no-ops (rule 2).

---

## Conflict Detection

(copied verbatim from SPEC §6.8 CONFLICT rule)

> Conflict detection rule (normative): two entries on the same "subject" with incompatible content. The ingest prompt defines "subject" as the topic the decision is about (e.g., TLS-vs-mTLS is one subject; port choice is a different subject). Heuristics are encouraged; exact ML matching is out of scope.

### "Same subject" definition

Two entries are on the *same subject* iff they concern the same topic-key. A topic-key is the subject of the decision, constraint, or requirement, identified by extracting the noun-phrase of the thing being decided. The ingest-writer (running `prompts/PROMPT-orch-ingest.md`) is responsible for computing topic-keys heuristically; the protocol does not require an exact matcher.

Illustrative list of topic-keys (NOT exhaustive; the list is meant to make the heuristic concrete, not to constrain it):

- `transport.security` — choice of TLS vs mTLS vs plaintext, for any transport in the task
- `transport.protocol` — choice of HTTP vs gRPC vs QUIC vs WebSocket, for any transport
- `cert.rotation` — certificate lifecycle / rotation mechanism
- `port.alloc` — port number assignment, allocation policy, or port ranges
- `auth.method` — authentication mechanism (token, mTLS, OAuth, etc.)
- `sync.layout` — the layout of the sync protocol itself (this file, the templates, the prompts)

Two entries on the same topic-key with incompatible content (e.g., "use TLS" and "use mTLS" both under `transport.security`, with neither `revises:`-ing the other) are a CONFLICT. Two entries on different topic-keys are never a CONFLICT by subject, even if their wording overlaps.

The list above is illustrative; the real topic-key set is whatever the ingest-writer's heuristic produces. Extractor-side, the heuristic is "did the human phrase this as a different topic or the same topic?". Ingest-side, the heuristic is "does this entry's topic-key match an existing ledger entry's topic-key, and if so, do their contents agree?". When the heuristic is uncertain, ingest should flag `CONFLICT` rather than silently `ACCEPT` — surfacing a false conflict is cheaper than missing a real one.

---

## Sync Payload Schema

(copied verbatim from SPEC §6.7)

```yaml
sync_id: 3                           # zero-padded on disk as 003.yaml; as int here
task_id: example-task-001
source: discussion                   # literal 'discussion'
created_at: 2026-08-14T20:30:00Z
status: pending                      # pending | applied | rejected | conflict

changes: {}                          # empty dict is allowed by schema, but rule 6.6.1 forbids writing such files

# Canonical example (one entry per allowed bucket):
# changes:
#   requirements:
#     - id: R-002
#       class: CONFIRMED
#       content: "…"
#       reason: "…"
#   decisions:
#     - id: D-003
#       class: CONFIRMED
#       content: "…"
#       reason: "…"
#       revises: null               # or "D-001"
#   constraints:
#     - id: C-001
#       class: CONFIRMED
#       content: "…"
#   progress:
#     - id: P-002
#       content: "…"
#       evidence: "path/to/file.md"
#   open_questions:
#     - id: Q-001
#       content: "…"
#   rejected:
#     - id: X-001
#       content: "…"
#       reason: "…"
```

---

## Where Each Category Lands

(copied verbatim from SPEC §6.9 — disposition ACCEPT)

| Category | Destination file | Destination section |
|---|---|---|
| `requirements` (CONFIRMED) | `task.md` | § Requirements |
| `decisions` (CONFIRMED) | `decisions.md` | § Decisions |
| `constraints` (CONFIRMED) | `decisions.md` | § Constraints |
| `progress` | `state.md` | § Completed (or § In Progress if `next_action` references it) |
| `open_questions` | `state.md` | § Open Questions |
| `rejected` | `decisions.md` | § Rejected |
| `PROPOSED` / `EXPLORATORY` (any of above) | sync payload only; not transcribed | — |

---

## The `/sync` User Gesture

The `/sync` gesture is how a human triggers extraction inside a Discussion Session. There is no custom slash command registered at this stage; `/sync` is a *prompt pattern*, not a feature. Two equivalent invocations:

### (a) Inline natural-language form

The human types one of:

- `/sync`
- `把刚才讨论与当前 task 有关的内容同步`
- `sync the task-relevant parts of the recent discussion`
- any equivalent phrasing the assistant recognizes as a sync request

The assistant then *behaves as if* the contents of `prompts/PROMPT-disc-extractor.md` had been invoked as its operating instruction. The assistant locates the prompt file (typically by reading `workflow/discussion-sync/prompts/PROMPT-disc-extractor.md`), reads it, and follows its procedure step by step.

### (b) Explicit prompt form

The human opens `workflow/discussion-sync/prompts/PROMPT-disc-extractor.md`, copies its full contents, and pastes it into the Discussion Session as a user message. The assistant then operates on those instructions directly.

### Note on slash-command registration

No custom slash command is registered at this stage. The Discussion Session has no native `/sync` built-in; the gesture works only when (a) the assistant recognizes the natural-language request and locates the prompt file, or (b) the human pastes the prompt file directly. A future task may register `/sync` as a true slash command; that is out of scope here.

---

## The Orchestrator Ingest Gesture

The ingest gesture is how sync payloads are processed into the ledger. Two equivalent invocations:

### (a) Manual — human pastes the ingest prompt

At the start of the Orchestrator Session for a task that has any `sync/*.yaml` with `status: pending`, the human opens `workflow/discussion-sync/prompts/PROMPT-orch-ingest.md`, copies its full contents, and pastes it into the Orchestrator Session as a user message. The Orchestrator then operates on those instructions directly, processing all pending payloads and emitting the per-file report and the plan-delta review.

### (b) Automated — task-start routine includes ingest

The orchestrator workflow's task-start routine (the part of `../workflow.md` §Dispatch Loop that runs when the Orchestrator picks up a task) MAY include a step: "before dispatching any worker, read `prompts/PROMPT-orch-ingest.md` and follow its procedure against `<task>/sync/*.yaml`." When this step is present, ingest runs at every task start without human intervention. When absent, the human must invoke ingest manually per (a).

In both forms, ingest is a *one-shot, blocking* operation: it runs to completion (or until it hits a `status: conflict`), then exits. It is not a daemon, not a file-watcher, not a slash command.

---

## Conformance Requirements

These are the MUSTs. Each is numbered R-1…R-n and is traceable to a § in this file. The verifier (V1) will cite these by number when checking SPEC §8 acceptance scenarios.

- **R-1** (traces to §Idempotency rule 1; satisfies SPEC A1, A4) — If the extractor computes that zero new task-relevant items exist beyond the ledger, it MUST NOT write any `sync/NNN.yaml` file and MUST reply to the human with a text message indicating "no new task-relevant changes since last sync".
- **R-2** (traces to §Entry Classes & Dispositions; satisfies SPEC A2) — Every entry inside `changes.{requirements,decisions,constraints}` MUST carry a `class:` field with exactly one of the values `CONFIRMED`, `PROPOSED`, `EXPLORATORY`, `IRRELEVANT`. `IRRELEVANT` entries MUST NOT appear in the payload at all.
- **R-3** (traces to §ID Conventions and §Incremental Sync; satisfies SPEC A2, A3) — Every entry emitted by the extractor MUST carry an ID not already present in the ledger (the union of IDs in `task.md`, `decisions.md`, `state.md`, and all `sync/*.yaml`). The extractor MUST compute the next `sync_id` as `max(existing sync_ids) + 1` and MUST NOT renumber or rewrite older sync files.
- **R-4** (traces to §Entry Classes & Dispositions and §Where Each Category Lands; satisfies SPEC A3) — Ingest MUST `ACCEPT` (i.e., transcribe into the ledger) only entries whose `class:` is `CONFIRMED`. `PROPOSED` and `EXPLORATORY` entries MUST remain in the payload only; they MUST NOT be transcribed into `task.md`, `decisions.md`, or `state.md`.
- **R-5** (traces to §Idempotency rule 2; satisfies SPEC A4, A6) — Ingest MUST scan `sync/*.yaml` for files whose `status: pending`, process them in ascending `sync_id` order, and rewrite each processed file's `status:` to exactly one of `applied`, `rejected`, or `conflict`. Ingest MUST NOT delete any sync file. Repeated ingest runs on a task with no `status: pending` files MUST be no-ops.
- **R-6** (traces to §Conflict Detection; satisfies SPEC A5) — When ingest encounters an entry on the same subject (per the heuristic topic-key definition in §Conflict Detection) as an already-applied ledger entry, with incompatible content and no `revises:` linking them, ingest MUST assign disposition `CONFLICT`, MUST NOT overwrite the existing ledger entry, MUST flip the payload's `status:` to `conflict`, and MUST surface the conflict to the human.
- **R-7** (traces to §Ordering & Versioning; satisfies SPEC A6) — Ingest MUST process pending sync files in ascending `sync_id` order and MUST NOT skip a gap. If `NNN.yaml` is missing while `NNN+1.yaml` exists, ingest MUST flag `missing_sync` and MUST NOT process past the gap.
- **R-8** (traces to §The Orchestrator Ingest Gesture; satisfies SPEC A6) — After all pending files are processed (or processing stopped at a conflict), the Orchestrator MUST review whether its current execution plan is still consistent with the new ledger and MUST emit an explicit plan-delta if the plan has been invalidated. The plan-delta is a text output, not a file mutation.
- **R-9** (traces to §Forbidden Categories and SPEC §14 A-1; satisfies SPEC A1, A3) — The extractor MUST NOT emit chitchat, social content, uncommitted musing without an explicit intent-to-log signal (classified `IRRELEVANT` per SPEC §14 A-1; e.g., "should we consider QUIC? unclear, need benchmarks"), purely exploratory `open_questions` (SPEC §14 A-1: `open_questions` are for genuine blocking questions only, never for exploratory musing), discarded alternatives without a recorded reason, duplicate IDs, or content not relevant to the current task.
- **R-10** (traces to §Incremental Sync; satisfies SPEC A2, A5) — To revise an existing ledger entry, the extractor MUST emit a new entry with `revises: <existing-ID>` set to the old ID and full replacement content; it MUST NOT reuse the old ID as the new entry's own ID.
- **R-11** (traces to §The `/sync` User Gesture; satisfies SPEC A1, A4) — `/sync` is a prompt pattern, not a registered slash command. The Discussion Session MUST recognize either (a) the inline natural-language form or (b) the explicit prompt-paste form, and in either case MUST operate on the contents of `prompts/PROMPT-disc-extractor.md`.

---

## §9 High-Risk Reasoning Ledger (P0)

status: FROZEN (P0). This section is self-contained: it changes nothing outside tasks that pass the High-Risk Reasoning Gate.

### Scope

This section is active only for tasks that pass the High-Risk Reasoning Gate (see `../workflow.md` §High-Risk Reasoning Gate). Normal tasks are unaffected. The sync payload schema (§Sync Payload Schema), the allowed categories (§Allowed Categories), and the idempotency rules (§Idempotency) are UNCHANGED by this section — reasoning entries travel inside the existing `decisions` bucket.

### Ledger Entry Types & Fields

Entries live in the task's `decisions.md`.

Prefix ownership: Decisions keep the legacy `D-XXX` prefix; Derivations use `DER-XXX`. The two live in the same ledger file but disjoint ID spaces.

**Assumption — `A-XXX`:**

- `content` — one sentence
- `source` ∈ {`user` | `spec` | `inference`} — required
- `status`
- `revises: A-YYY` — optional
- `reason` — required when invalid

**Derivation — `DER-XXX`:**

- `content`
- `from: [<ID>, ...]` — REQUIRED, ≥1 ID; may reference Assumption (`A-XXX`), Constraint (`C-XXX`), Derivation (`DER-XXX`), or Decision (`D-XXX`) IDs. A from-less conclusion is an Assumption or a Decision, not a Derivation.
- `by` — one-line method
- `verify` — one executable check: a fixture, a command, or a code-inspection target
- `status`
- `revises:` — optional
- `reason` — required when needs_review/invalid; must name the triggering upstream ID or verdict

**Constraint — `C-XXX`:**

- `content`
- `verify` — typically a code-inspection target
- `status`
- `from:` — usually absent (constraints are roots) but MAY be carried

**Decision — `D-XXX`** (existing `decisions` bucket):

- optional new field `basis: [<DER/A IDs>]` — when any basis entry flips invalid, the decision becomes needs_review. No other decision semantics change.

### Status Vocabulary

Four statuses: `proposed | valid | needs_review | invalid`. Per-type applicability:

| Entry type | Allowed statuses |
|---|---|
| Assumption | proposed, valid, invalid — roots: no needs_review |
| Derivation | proposed, valid, needs_review, invalid |
| Constraint | proposed, valid, needs_review, invalid |
| Decision | valid, needs_review, invalid |

### Birth-State Rules

- `source` ∈ {`user`, `spec`} → born `valid`
- `source` = `inference` → born `proposed`
- Derivations are always authored by agents → born `proposed`
- Decisions are user-authored → born `valid`

Promotion `proposed` → `valid` happens ONLY via (a) user confirmation, or (b) a Verdict PASS targeting the entry. There is no other promotion path.

### Invalid Sources — Closed Set

An entry may become `invalid` ONLY from: {a Verdict FAIL targeting it, a user declaration, supersession by a new entry carrying `revises:`}. Agent natural-language doubt NEVER invalidates; it produces a proposed counter-entry or an Open Question.

### Validity Invariant

An entry may be `valid` only if every ID in its `from:` / `basis:` is currently `valid`.

### Append-Only & Write Authority

- Entry content is never edited in place; a change is a new entry + `revises:`.
- The `status:` field is written ONLY by the orchestrator.
- Verdicts are written ONLY by verifier sessions.
- Entry content is written by workers.

### Verdict Semantics

Verdicts live in `evaluation.md` `## Verdicts`, with fields {`id`, `target` (single ID, mandatory), `method`, `expected`, `actual`, `verdict: PASS|FAIL`, `evidence` (path), `author`}. PASS means "the workflow may continue using the target under current evidence", NOT mathematical proof. An empty or multi-target verdict is invalid.

### Invalidation Protocol

An orchestrator obligation, executed at ingest or at an explicit reasoning sweep — no watchers, no daemons.

- **Step 0 SWEEP** — git-diff the task dir (`decisions.md`, `evaluation.md`, `state.md`) since last ingest; any hand-edit of status fields or of `state.md` `## Reasoning State` by a non-orchestrator is a violation → restore by mechanical regeneration and record an ESCALATE.
- **Step 1 SEED** — collect the IDs that flipped to invalid in this cycle (Verdict FAIL targets, user-invalidated entries, superseded entries).
- **Step 2 CLOSURE** — iteratively grep `decisions.md` for entries whose `from:`/`basis:` contains any seed/affected ID, until fixpoint; mark each hit `needs_review` with `reason:` = the triggering upstream ID (skip entries already invalid). **FREEZE RULE: closure expands only from `invalid` seeds — `needs_review` itself never triggers further propagation.**
- **Step 3 BLOCK** — affected IDs ∩ `evaluation.md` `## Implementation Map` targets → a set of `file::symbol` → write into `state.md` `## Blocked`.
- **Step 4 REGEN** — mechanically regenerate `state.md` `## Reasoning State` (valid assumptions / frontier valid derivations / needs_review with reasons / invalid with one-word reasons / open verifications / proposed pending). This section is a pure projection — never hand-maintained.
- **Step 5 NOTIFY+GATE** — subsequent worker prompts carry the updated snapshot; do not dispatch work touching Blocked symbols; in-flight workers are not interrupted (their prompts are self-contained) — verifier diff-checks backstop them.
- **Step 6 RESOLVE** — dispatch a reasoning worker to re-derive (new ID + `revises:`); the verifier re-runs the `verify:` checks; on Verdict PASS flip statuses per the state machine and regenerate projections; repeat until closure empties.

### Known P0 Residual Risks

(a) status/projection write-authority is enforced by sweep-detection + regeneration, not by physical read-only access; (b) Blocked-scope is enforced by prompt rule + verifier diff-grep + judge spot-checks, not by automatic interception. Both are accepted P0 trade-offs and P1 upgrade candidates.
