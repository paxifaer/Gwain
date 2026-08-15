# ARCHITECTURE — Discussion–Orchestrator Sync

status: design doc for SPEC `discussion-sync` (SPEC-discussion-sync.md, user-approved 2026-08-14).
scope: this file is normative for *what* the sync protocol is and *why* it has its current shape; `protocol.md` is normative for *how* to conform. If the two ever appear to disagree, `protocol.md` wins for conformance and this file is the bug.

---

## Purpose

The Discussion–Orchestrator Sync (hereafter *the sync protocol*) is a file-only bridge between two Claude Code sessions that serve different roles: a **Discussion Session**, where a human explores options freely, and an **Orchestrator Session**, which executes a task against distilled state. It exists so the Orchestrator's context never has to absorb the full back-and-forth of a Discussion; instead, only structured deltas — Decisions, Constraints, Requirements, Progress, Open Questions, Rejected alternatives — cross the boundary, written as numbered YAML payloads that the Orchestrator ingests idempotently. The protocol is opt-in per task; a task that does not create the layout described in `protocol.md` §Task-State Layout is simply not participating, and nothing else in the workflow changes.

---

## Actors

### Discussion Session

The Discussion Session is the human-facing thinking space: a single Claude Code conversation in which the human and the assistant explore options, propose choices, raise questions, and eventually confirm or reject ideas. It is *not* a worker; it does not run tests, edit code, or dispatch sub-tasks. Its only obligation under this protocol is that, when the human wants to push the task-relevant subset of the conversation toward the Orchestrator, it runs the extractor prompt (`prompts/PROMPT-disc-extractor.md`) and writes at most one new numbered YAML payload into the task's `sync/` directory. The Discussion Session never mutates `task.md`, `decisions.md`, or `state.md` — those are the Orchestrator's ledger.

### Orchestrator Session

The Orchestrator Session is the task-facing execution space: it plans, dispatches workers, and judges results, as defined in `../workflow.md`. Under this protocol it gains one extra responsibility — at task start (or whenever the human says `/ingest`), it runs the ingest prompt (`prompts/PROMPT-orch-ingest.md`) against any `sync/*.yaml` files whose `status: pending`. Ingest assigns each entry in each pending payload a disposition (ACCEPT / MERGE / REJECT / CONFLICT), mutates the ledger files (`task.md`, `decisions.md`, `state.md`) exactly as the disposition dictates, and rewrites the payload's `status:` field to `applied` / `rejected` / `conflict` — never deleting it. After ingest, the Orchestrator reviews whether its current execution plan is still consistent with the new ledger and emits an explicit plan-delta if not.

### Task Ledger

The Task Ledger is not a process; it is the union of three files on disk: `<task>/task.md` (Goal / Scope / Requirements / Acceptance Criteria), `<task>/decisions.md` (D-XXX decisions, C-XXX constraints, X-XXX rejected), and `<task>/state.md` (Status, Completed, In Progress, Blocked, Next Action, Open Questions). For high-risk tasks (`protocol.md` §9) the ledger surface extends factually: `decisions.md` additionally carries Assumptions and Derivations sections, constraints may carry `verify:`/`status:`, and decisions may carry `basis:`; `state.md` gains `## Reasoning State`, an orchestrator-generated projection; `evaluation.md` gains `## Verdicts` and `## Implementation Map`. It is the single authoritative record of task state. Every conformance check in this protocol reduces to "does the ledger, read in ascending order, contain this ID with this content?" The ledger is append-mostly: ingest may annotate or supersede a prior line, but it does not delete history — a revision is a new line that names the old one in its `revises:` field.

---

## Data Flow

```
                         Discussion Session
                                |
                  human: "/sync" (or NL equivalent)
                                |
                                v
                  +-------------------------+
                  | PROMPT-disc-extractor   |   reads:  task.md, decisions.md,
                  +-------------------------+            state.md, sync/*.yaml
                                |            (union of IDs = ledger)
                                |
                  writes ONE new file (if non-empty):
                                |
                                v
                  <task>/sync/NNN.yaml  (status: pending)
                                |
                                |   (time passes; Orchestrator starts task)
                                v
                  Orchestrator Session
                                |
                  human: "/ingest"  OR  task-start routine
                                |
                                v
                  +-------------------------+
                  | PROMPT-orch-ingest      |   reads:  sync/*.yaml ascending,
                  +-------------------------+            task.md, decisions.md,
                                |                       state.md
                                | per entry: ACCEPT / MERGE / REJECT / CONFLICT
                                |
         +----------------------+------------------------+
         |                      |                        |
         v                      v                        v
   task.md /            decisions.md /             state.md /
   decisions.md         state.md                  sync/NNN.yaml
   (ledger mutated)     (ledger mutated)          (status: applied |
                                                  rejected | conflict)
                                |
                                v
                  plan-delta review
                  (Orchestrator re-plans if ledger drift detected)
```

**Arrow 1 — human gesture to Discussion Session.** The human types `/sync` or a natural-language equivalent such as "把刚才讨论与当前 task 有关的内容同步". No custom slash command is registered at this stage; `/sync` is a *prompt pattern*, not a feature. The Discussion Session assistant then behaves as if `prompts/PROMPT-disc-extractor.md` had been invoked.

**Arrow 2 — extractor reads the ledger.** The extractor's first job is to construct the ledger: it reads `<task>/task.md`, `<task>/decisions.md`, `<task>/state.md`, and every `<task>/sync/*.yaml` (any status), and takes the union of all item IDs (R-/D-/C-/P-/Q-/X-) referenced. This union is the *ledger* against which idempotency is computed.

**Arrow 3 — extractor writes one new file.** If the extractor finds at least one new task-relevant CONFIRMED/PROPOSED/EXPLORATORY entry not already in the ledger, it writes exactly one new file `<task>/sync/<NNN+1>.yaml` with `status: pending`. If it finds zero new content, it writes nothing and replies with a fixed phrase. The extractor never mutates existing files.

**Arrow 4 — time passes.** Sync payloads sit on disk with `status: pending` until the Orchestrator next runs ingest. There is no daemon, no file watcher, no push notification. The boundary between Discussion and Orchestrator is intentionally asynchronous.

**Arrow 5 — Orchestrator invokes ingest.** At task start (or on explicit `/ingest`), the Orchestrator runs `prompts/PROMPT-orch-ingest.md`. Ingest reads `sync/*.yaml` sorted ascending and processes only files with `status: pending`.

**Arrow 6 — per-entry disposition mutates the ledger.** For each entry in each pending payload, ingest assigns ACCEPT / MERGE / REJECT / CONFLICT and mutates the corresponding ledger file (`task.md` for confirmed requirements, `decisions.md` for confirmed decisions/constraints/rejected, `state.md` for progress/open_questions) exactly as `protocol.md` §Where Each Category Lands dictates.

**Arrow 7 — payload status rewritten.** After processing a file, ingest rewrites its `status:` to `applied`, `rejected`, or `conflict`. The file is never deleted; it remains as the durable record of what was proposed and how it landed.

**Arrow 8 — plan-delta review.** After all pending files are processed (or processing stopped on a conflict), the Orchestrator reviews its current execution plan against the new ledger and emits an explicit plan-delta if the plan has been invalidated (e.g., a confirmed decision contradicts an in-progress worker's assumed constraint).

---

## File Surfaces

| File | Introduced by | Mutated by | Mutated when |
|---|---|---|---|
| `workflow/discussion-sync/ARCHITECTURE.md` | this task (W1) | humans only | design changes |
| `workflow/discussion-sync/protocol.md` | this task (W1) | humans only | protocol revisions |
| `workflow/discussion-sync/templates/task.md` | this task (W1) | template; copied into `<task>/task.md` by W2 / human | new task setup |
| `workflow/discussion-sync/templates/state.md` | this task (W1) | template; copied into `<task>/state.md` | new task setup |
| `workflow/discussion-sync/templates/decisions.md` | this task (W1) | template; copied into `<task>/decisions.md` | new task setup |
| `workflow/discussion-sync/templates/evaluation.md` | this task (W1) | template; copied into `<task>/evaluation.md` | new task setup |
| `workflow/discussion-sync/templates/sync-NNN.yaml` | this task (W1) | template; copied as `<task>/sync/NNN.yaml` | each `/sync` |
| `workflow/discussion-sync/prompts/PROMPT-disc-extractor.md` | this task (W1) | humans only | prompt revisions |
| `workflow/discussion-sync/prompts/PROMPT-orch-ingest.md` | this task (W1) | humans only | prompt revisions |
| `<task>/task.md` | opting-in task setup | Orchestrator ingest (ACCEPT of confirmed `requirements`) | per-ingest |
| `<task>/state.md` | opting-in task setup | Orchestrator ingest (ACCEPT of `progress` / `open_questions`); Orchestrator during task | per-ingest + per-step |
| `<task>/decisions.md` | opting-in task setup | Orchestrator ingest (ACCEPT of confirmed `decisions` / `constraints` / `rejected`) | per-ingest |
| `<task>/evaluation.md` | opting-in task setup | mostly static; human / verifier at task close | task close |
| `<task>/sync/NNN.yaml` | Discussion extractor (writes new `NNN+1.yaml`) | Orchestrator ingest (rewrites `status:` only) | `/sync` then ingest |
| `workflow/workflow.md` | this task (W1, append-only § only) | humans only | never by this protocol again |

A file that does not appear in this table is not part of the protocol. In particular, there is no separate "registry" file, no "cursor" file, and no "ingest log" — the sync files themselves, with their `status:` field, are the registry.

---

## Design Decisions

Each decision below lists the chosen option, the rejected alternative(s), the tradeoff (what breaks or becomes awkward under the chosen option), and the protocol/prompt file path where the decision is enforced.

**D-1 — Ledger-based sync, not cursor-based.**
*Chosen:* The extractor receives the union of all IDs already present in `task.md` / `decisions.md` / `state.md` / applied `sync/*.yaml`, and may only emit entries whose IDs are not already in that union. There is no "give me everything since timestamp T" mode.
*Rejected:* A conversation-cursor API that hands the extractor "messages since checkpoint C". *Tradeoff:* Without a cursor, the extractor must re-scan the entire ledger on every `/sync`, which is O(ledger) per call. With a cursor, we'd need a checkpoint API Claude Code does not expose; rolling our own would require either a persisted timestamp (fragile across sessions) or a message-id log (which is itself a new state file the protocol would have to manage). Ledger-scans are cheaper than the alternative.
*Enforced at:* `protocol.md` §Incremental Sync; Ledger Not Cursor; `prompts/PROMPT-disc-extractor.md` §Inputs.

**D-2 — The `class` field lives on entries, not on the payload.**
*Chosen:* Every entry inside `changes.{requirements,decisions,constraints}` carries its own `class:` (`CONFIRMED` / `PROPOSED` / `EXPLORATORY` / `IRRELEVANT`). The payload as a whole has no class.
*Rejected:* A payload-level `class:` ("this whole sync is EXPLORATORY"). *Tradeoff:* Per-entry class is more verbose and forces the extractor to classify each item individually. But a single Discussion often mixes classes (the human confirms one thing, explores another, proposes a third); a payload-level class would force `/sync` to split into three files, tripling the ingest workload and breaking the "one `/sync` = one file" mental model. Per-entry class lets one payload carry mixed maturity.
*Enforced at:* `protocol.md` §Entry Classes & Dispositions; `templates/sync-NNN.yaml`; `prompts/PROMPT-disc-extractor.md` §Rules.

**D-3 — Only `CONFIRMED` entries auto-transcribe into the ledger.**
*Chosen:* ACCEPT (i.e., write into `task.md` / `decisions.md` / `state.md`) is the disposition for `CONFIRMED` entries only. `PROPOSED` and `EXPLORATORY` entries ride in the payload, get their `status:` flipped to `applied`, but are not transcribed — they live in `sync/NNN.yaml` only. The ledger remains the set of things the human actually committed to.
*Rejected:* Auto-transcribe `PROPOSED` into `decisions.md` with a `?` marker, or auto-transcribe `EXPLORATORY` into `state.md § Open Questions`. *Tradeoff:* PROPOSED/EXPLORATORY content is invisible from the ledger, so a human scanning `decisions.md` for "what have we committed to?" must also remember to grep `sync/*.yaml` for the exploratory record. The alternative blurs the line between "decided" and "discussed" and silently pollutes the ledger with non-decisions. The cost of clean separation is a two-place lookup for full history.
*Enforced at:* `protocol.md` §Where Each Category Lands; `prompts/PROMPT-orch-ingest.md` §Procedure.

**D-4 — The payload's `status:` field is the registry; there is no separate registry file.**
*Chosen:* Each `sync/NNN.yaml` carries a `status:` field (`pending` / `applied` / `rejected` / `conflict`). Ingest scans for `status: pending`, processes, and rewrites the same field in place. No `sync/registry.yaml`, no `sync/index.json`.
*Rejected:* A separate `sync/registry.yaml` that maps `sync_id → status`. *Tradeoff:* Two files must stay in sync (the payload and the registry), and a registry update can fail independently of the payload rewrite, leaving a window where the registry says `applied` but the payload still says `pending`. The chosen approach makes the payload *self-describing*: one read tells you everything. Cost: rewriting a YAML file in place means the file's mtime bumps on ingest, but that's fine — mtime is not load-bearing in this protocol.
*Enforced at:* `protocol.md` §Sync Payload Schema; `prompts/PROMPT-orch-ingest.md` §Procedure (steps on `status:` rewrite).

**D-5 — `decisions.md` hosts Decisions, Constraints, and Rejected in one file; not three.**
*Chosen:* `decisions.md` has five sections: Decisions (D-XXX), Constraints (C-XXX), Rejected (X-XXX), Assumptions (A-XXX), Derivations (DER-XXX). There is no separate `constraints.md`, `rejected.md`, `assumptions.md`, or `derivations.md`.
*Rejected:* One file per category: `decisions.md`, `constraints.md`, `rejected.md`. *Tradeoff:* `decisions.md` is three-ways-sectioned, which is a slightly awkward shape; cross-section references (a Decision that cites a Constraint) must use the same file. The alternative triples the file count per task and forces every cross-reference to be a file-path instead of a section-anchor. The latter is more annoying for the LLM to write and grep. One file is the smaller cognitive load.
*Enforced at:* `protocol.md` §Where Each Category Lands; `templates/decisions.md`; `prompts/PROMPT-orch-ingest.md` §Procedure.

**D-6 — Ingest runs inside a worker at Orchestrator task-start; not via a daemon.**
*Chosen:* There is no background process watching `sync/`. Ingest is invoked by a human (paste of `prompts/PROMPT-orch-ingest.md`) or by the orchestrator workflow's task-start routine. It runs to completion and exits.
*Rejected:* A file-watcher daemon or an MCP server that triggers ingest on file create. *Tradeoff:* Pending sync payloads can sit unread indefinitely if no one runs ingest — there is no automatic push toward the Orchestrator. The alternative requires a long-running process, which the SPEC (§2 Non-Goals) explicitly forbids ("No MCP server / database / runtime service"). The cost is acceptable: a human who runs `/sync` in Discussion is by definition interactive, and can be expected to also start the Orchestrator session that consumes the payload.
*Enforced at:* `protocol.md` §The Orchestrator Ingest Gesture; `prompts/PROMPT-orch-ingest.md` §Explicit non-goals.

**D-7 — No deduplication of entries by content hash.**
*Chosen:* Two entries are "the same" iff their IDs are the same. The extractor computes the next-free ID and may emit a fresh ID for what a human might consider "the same idea rephrased". There is no content-hash check that says "this new entry's content hashes equal to an existing ledger entry, so skip it".
*Rejected:* Hash the content of every new entry, compare against hashes of existing ledger entries, suppress duplicates by hash. *Tradeoff:* A human who says the same thing twice with different wording will produce two entries. The alternative requires the extractor to maintain a hash index of the ledger and to judge "same" — which is a semantic call, not a byte call, and LLMs are bad at being consistent about it. Worse, a hash check could suppress a legitimate *re-statement with a refinement*. IDs are the only identity we trust; everything else is heuristic.
*Enforced at:* `protocol.md` §Idempotency (rule 1, "zero new content" is the only idempotency guarantee); `prompts/PROMPT-disc-extractor.md` §Rules.

**D-8 — Opt-in task layout, not mandatory.**
*Chosen:* A task adopts the new `task.md` / `state.md` / `decisions.md` / `evaluation.md` / `sync/` layout by *creating* those files. A task that does not create them keeps using the legacy `SPEC-*.md + PROMPT-* + logs` convention. Nothing in `workflow.md` forces a new task to opt in.
*Rejected:* Make the new layout the default for all new tasks; require legacy tasks to declare "I'm staying old-style". *Tradeoff:* Two layout conventions coexist in the repo indefinitely, which is mildly confusing for someone reading the codebase cold. The alternative forces every new task to do setup work it may not need (a one-shot worker task doesn't need a Discussion–Orchestrator split). The protocol earns its keep only on tasks that have real Discussion overhead; opt-in lets the cost fall only on those tasks.
*Enforced at:* `workflow.md` §Discussion Session Sync (Opt-in); `protocol.md` §Scope & Non-goals.

---

## Known Limitations

1. **No automatic conflict subject-matching — heuristic only.** *Limitation:* The protocol requires ingest to flag `CONFLICT` when a new entry "semantically contradicts an already-applied ledger entry on the same subject". But "same subject" is computed by the ingest-writer's heuristic (see `protocol.md` §Conflict Detection for an illustrative topic-key list), not by an exact matcher. A subtle restatement can slip past the heuristic and be ACCEPTed when it should CONFLICT.
   *Mitigation:* The plan-delta review step (the final step of `PROMPT-orch-ingest.md`) is a second look: even if a CONFLICT was missed at entry-level, the Orchestrator's broader view of the ledger may catch the inconsistency and surface it to the human. *Status:* accepted — exact ML subject matching is out of scope per SPEC §6.8.

2. **Ledger grows unbounded; no garbage collection.** *Limitation:* `decisions.md` and `sync/*.yaml` are append-mostly and never pruned. A long-running task will accumulate dozens of sync files and a `decisions.md` hundreds of lines long. The ledger scan inside the extractor is O(ledger), so per-`/sync` cost grows linearly with task age.
   *Mitigation:* `state.md` has an explicit ≤ 60 line cap (see `templates/state.md`); when exceeded, archive to `state.archive.md` and restart. No equivalent cap exists for `decisions.md` or `sync/`; if a task grows past the point where ledger scans are slow, the human can manually archive old `sync/*.yaml` files into a `sync/archive/` subdirectory (the extractor only reads `sync/*.yaml` at the top level, so archived files leave the ledger). *Status:* accepted — no automatic GC in this version.

3. **No cross-task dependencies.** *Limitation:* A task's ledger is local to that task. There is no protocol for "this task's D-005 depends on another task's D-002". If two tasks share a constraint, each task records its own C-XXX independently, and the two can drift.
   *Mitigation:* The human is responsible for cross-task consistency; the Orchestrator's plan-delta review can flag if a worker reports a contradiction with another task's known state. *Status:* accepted — cross-task state is out of scope per SPEC §2 ("No migration of existing tasks ... stay as-is").

4. **The Discussion Session has no native `/sync` slash command — it is a prompt pattern, not a feature.** *Limitation:* Typing `/sync` is *not* a registered slash command in the Discussion Session. It works only because the human and the assistant share the convention that `/sync` means "behave as if `prompts/PROMPT-disc-extractor.md` had been pasted as a user message". A Discussion Session that has never seen the prompt file will not know what `/sync` means.
   *Mitigation:* The Discussion Session's system prompt or first user message should include (or reference) `prompts/PROMPT-disc-extractor.md` so the `/sync` gesture is defined in-context. Alternatively, the human can paste the prompt file's contents directly. *Status:* accepted — no slash-command registration in this version per SPEC §6.6/§7.

5. **Idempotency depends on extractor honesty, not on filesystem locks.** *Limitation:* SPEC L3 says repeated `/sync` on the same Discussion state MUST NOT produce a new payload. The protocol enforces this by *instructing* the extractor (in `prompts/PROMPT-disc-extractor.md` §Rules) to compute the ledger and to write nothing if zero new content. There is no filesystem lock, no atomic compare-and-swap, no write barrier that *prevents* a misbehaving extractor from writing a duplicate. If the extractor hallucinates a new entry, idempotency breaks.
   *Mitigation:* `PROMPT-orch-ingest.md`'s idempotency check ("skip entries whose ID already exists in ledger") is the second line of defense — even if the extractor wrongly emits a duplicate-ID entry, ingest will skip it rather than double-write. The two checks together cover both the "extra file written" failure (covered by ingest skipping duplicates) and the "extra entry in a legitimate file" failure (also covered). The one failure mode not covered is an extractor that emits a *new ID* with *content equivalent to an existing entry* — that is limitation 7 above. *Status:* accepted — filesystem locking is out of scope; the SPEC explicitly forbids new binaries/daemons.

6. **Ingest is blocking and serial.** *Limitation:* Ingest processes `sync/*.yaml` in ascending order and stops at the first `status: conflict`. If `005.yaml` conflicts, `006.yaml` and `007.yaml` are not processed on this run, even if they are independent of the conflict.
   *Mitigation:* The human resolves the conflict (rewrite or delete `005.yaml`, or annotate the ledger), then re-runs `/ingest`. The next run skips `005.yaml` (now `applied`/`rejected`) and processes `006.yaml` onward. *Status:* accepted — parallel ingest would make ledger mutation non-serializable.

7. **No automatic rollback of partial ingest.** *Limitation:* If ingest ACCEPTs three entries from `005.yaml` into `decisions.md` and then hits a CONFLICT on the fourth entry, the three accepted entries are already in the ledger. The protocol does *not* roll them back. The file `005.yaml` ends up `status: conflict` but the ledger has the three new lines.
   *Mitigation:* This is by design — the three accepted entries are correctly transcribed; only the fourth is contested. A human who wants the three un-done must issue a new sync payload with `revises:` entries that supersede them. *Status:* accepted — partial progress is preferred over all-or-nothing, since the conflict may take human time to resolve.

---

## Future MCP Migration Point

From SPEC §13, verbatim:

```
Current implementation
        ↓
File-based Sync Protocol
        ↓
If multi-agent / cross-machine requirements emerge
        ↓
CLI/API wrapper first
        ↓
Task State MCP only after that wrapper exists in use
```

This task does NOT build step 2, 3, or 4. ARCHITECTURE.md must include this trajectory verbatim.

**The concrete interface seam.** The protocol is structured so that *every* state-mutating operation goes through one of two prompt files: `prompts/PROMPT-disc-extractor.md` (writes one new `sync/NNN.yaml`) and `prompts/PROMPT-orch-ingest.md` (reads `sync/*.yaml`, mutates ledger, rewrites `status:`). These two prompts are the seam.

A future CLI wrapper would replace the human-pastes-prompt step with a binary that exposes the same two operations as commands:

```
gawain-sync extract  --task <task_id>      # replaces /sync; reads ledger, writes sync/NNN+1.yaml
gawain-sync ingest   --task <task_id>      # replaces /ingest; reads sync/*.yaml, mutates ledger
gawain-sync status   --task <task_id>      # read-only: prints pending count, last conflict
```

The function signatures these wrap would be:

```python
# Extractor side
def extract(task_dir: Path) -> Path | None:
    """Read <task_dir>/{task.md,decisions.md,state.md,sync/*.yaml}.
    Return path of newly-written sync/NNN+1.yaml, or None if no new content."""

# Ingest side
def ingest(task_dir: Path) -> IngestReport:
    """Process pending sync/*.yaml ascending; mutate ledger; rewrite statuses.
    Stop at first conflict. Return per-file disposition report."""
```

A later MCP server would expose those same two functions as tools (`gawain_extract`, `gawain_ingest`) plus a read-only `gawain_ledger_snapshot` tool. The YAML schema in `templates/sync-NNN.yaml` and the file layout in `protocol.md` §Task-State Layout are *already* the wire format — the MCP server would not introduce a new schema, only a new transport. That is the migration point: the schema stays, the prompt file becomes a tool invocation.
