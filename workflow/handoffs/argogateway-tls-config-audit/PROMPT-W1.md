# PROMPT-W1 — ArgoGateway TLS-mode config audit (investigation worker)

> Paste the worker-preamble at top, then the task-specific slots below.
> The worker-preamble's bootstrap path has been adjusted to this repo's actual location.

## Worker preamble (prepend to task prompt when dispatching)

```text
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's four questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
5. Code you write that participates in a cross-boundary integration test
   MUST follow the Integration Traceability Contract at
   /home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md
   (read it before writing any logging call). This task writes NO code, so
   the contract is not directly triggered; you do not need to emit events.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger. (This task has no state.md.)
```

## Who
You are the **W1 investigation worker** for the Gawain task
`argogateway-tls-config-audit`. You do code reading and gap analysis only. You
do not edit any source code. You produce one markdown report.

## What
Read the SPEC in full first:
`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/SPEC.md`

Then execute the investigation described there. Concretely:

1. Read `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
   end-to-end. Enumerate every place where the script branches on TLS vs
   plaintext. Each branch is one "delta" — record file:line, what TLS mode
   produces, what plaintext mode produces.

2. Locate the ArgoDDS / ArgoGateway configuration surface in
   `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/`. Start from
   `AGENTS.md` / `CLAUDE.md` if present. Then search for code that builds,
   edits, sends, or persists argodds / argogateway config — Tauri commands,
   Rust crates, TS packages, UI handlers. The user's phrase was "click TLS" so
   look for a TLS toggle / switch / checkbox in the UI layer and trace what it
   does.

3. For each delta from step 1, check whether `robot-app-platform` mirrors it
   when the user toggles TLS. Record a `YES` (mirrored, cite file:line + ≤3
   line snippet), `NO` (not mirrored — gap), or `PARTIAL` (mirrored in some
   code paths but not all).

4. Note any TLS-mode concern that `robot-app-platform` handles but
   `install_cluster.sh` does not (symmetric gap).

5. For each `NO` / `PARTIAL`, write a recommendation: what should be added or
   changed. **Describe in prose, do not write the code.** The user will decide
   whether to dispatch a follow-up Develop worker.

## Why
The user is asking whether the frontend's "click TLS" UX generates a config
that is actually different in TLS mode, in every place where the canonical
deploy script `install_cluster.sh` also differs. If the frontend just flips a
flag and doesn't adjust the surrounding config, deploying via the frontend
would produce a broken or insecure TLS setup. Your report gives the user the
evidence to decide whether to fix the frontend.

## Constraints
- **Read-only on all source code.** No `Edit`, no `Write` to source files.
- **Write-set = exactly one file:**
  `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/W1-REPORT.md`
- No `git` operations. No network. No tests run. No code execution beyond
  reading files and grepping.
- If you encounter an ambiguous code path that could be read two ways, pick
  the more conservative reading and record it as an ESCALATE in §8 of the
  report. Do not guess silently.
- HEAD-guard does not apply (you do not touch git).

## Inputs
- SPEC: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/SPEC.md`
- Reference script: `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
- Target codebase: `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/`
  - Suggested entry points: `AGENTS.md`, `CLAUDE.md`, `crates/`, `packages/`, `apps/`
  - Search hints: `argodds`, `argogateway`, `argo_tls`, `tls`, `plaintext`, `Transport`, `TlsConfig`, `cert`, `mTLS`
- Optional context (only if it helps): prior session jsonl is at
  `/home/wangdang/.claude/projects/-home-wangdang-work-ai-stack/5e6aa030-0e81-4186-80d4-dc5d14c9f275.jsonl`
  — but reading the whole session is not required. Use `grep` for `argo_tls.rs`
  or `install_cluster` mentions if you need extra context.

## Output contract
1. Write the report file at the declared path with the 8 sections defined in
   the SPEC (Summary / Method / Q1 / Q2 / Q3 / Q4 / Recommendations / ESCALATEs).
2. In your final message to the orchestrator, return:
   - One-line verdict: `GAP` / `NO-GAP` / `PARTIAL`
   - Counts: `<N>` deltas in Q1, `<M>` mirrored, `<K>` gaps, `<L>` partial
   - Path to the report file
   - Any ESCALATEs (one line each)
   - Elapsed time
   - Total length ≤ 200 words. Do not paste the report into the message —
     the orchestrator will dispatch V1 to read the file and verify.

## Verification
A verifier worker (V1) will be dispatched after you. V1's mandate is to
**disprove** your claims — for every file:line you cite, V1 will open the file
and check that the line exists and the snippet matches. Any fabricated line or
mis-attribute will cause V1 to return FAIL and the orchestrator will re-dispatch
you. Cite carefully.
