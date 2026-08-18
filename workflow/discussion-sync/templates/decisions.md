<!--
decisions.md — the task ledger for Decisions, Constraints, and Rejected.

USAGE
  Copy this file to <task>/decisions.md. Ingest mutates it by appending
  lines to the appropriate section when a sync payload entry is
  dispositioned ACCEPT (for CONFIRMED decisions / constraints / rejected)
  or MERGE (for revises: entries — old line kept, new line added).

ENTRY FORMAT (one line per entry, grep-friendly)
  Decisions   : - D-XXX — <content> — <reason> [revises: D-YYY]
  Constraints : - C-XXX — <content> — <reason>
  Rejected    : - X-XXX — <content> — <reason>

REVISIONS CHAIN
  When a decision revises an older one, the new line includes a
  `revises: D-YYY` marker at the end. The old line stays in place; it is
  not deleted. A reader following the chain greps for `revises: D-YYY` to
  find the superseding decision, and greps for `D-YYY` to find the
  original. Never edit an old line to mark it superseded — the chain is
  visible by reading both lines.

This file has five sections: Decisions, Constraints, Rejected, Assumptions,
Derivations. There is no separate constraints.md or rejected.md.
-->
<!--
GLOBAL RULES (high-risk reasoning extension)
  The `status:` field of every entry in this file is written ONLY by the
  orchestrator; entry content is written by workers; existing entries are
  never edited in place (append-only — supersede via a new entry with
  `revises:`).
-->

# Decisions

<!-- Entries MAY carry `basis: [<DER/A IDs>]` recording which derivations/assumptions justify the choice; when any basis entry flips to invalid, the decision becomes `needs_review` (set only by orchestrator); decisions are user-authored and born `valid`. -->

- (none yet)

# Constraints

<!-- Entries MAY carry `verify:` (typically a code-inspection target, e.g. `verify: code inspection base_b1p0.rs::waypoint_gen — steering target taken from reference twist`) and `status:` with the same vocabulary as Derivations (proposed|valid|needs_review|invalid); constraints usually have no `from:` (they are roots), but MAY carry one when justified by a derivation. -->

- (none yet)

# Rejected

- (none yet)

# Assumptions

<!--
ENTRY FORMAT (one line per entry, grep-friendly)
  - A-XXX — <single-sentence premise> — source: <user|spec|inference> — status: <proposed|valid|invalid> [revises: A-YYY] [reason: <why invalid>]

Append-only ledger; `source: inference` entries MUST be born `proposed`; proposed → valid ONLY via user confirmation or a Verdict PASS targeting this entry; assumptions have no `needs_review` (they are roots — nothing above them can flip); `invalid` may only arise from {Verdict FAIL, user declaration, superseded via revises:}; `reason:` is required when status is invalid.
-->

- (none yet)

# Derivations

<!--
ENTRY FORMAT (one line per entry, grep-friendly)
  - DER-XXX — <single-sentence conclusion> — from: [<ID>, ...] — by: <one-line method> — verify: <one executable check: fixture / command / code-inspection target> — status: <proposed|valid|needs_review|invalid> [revises: DER-YYY] [reason: <trigger>]

`from:` is MANDATORY and must contain ≥1 ID referencing any Assumption/Constraint/Derivation/Decision entry — a from-less conclusion is an Assumption or a Decision, not a Derivation; derivations are born `proposed` and promote to `valid` only via Verdict PASS; `needs_review` is set ONLY by the orchestrator when an upstream ID in `from:` flips to invalid (it is never set by workers and never propagates further transitively on its own); `reason:` is required for needs_review/invalid and must name the triggering upstream ID or verdict; when an entry is superseded, write a NEW entry with `revises:` — never edit the old entry's content.
-->

- (none yet)
