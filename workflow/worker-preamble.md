# Worker Preamble — paste at the top of every Gawain worker prompt

Orchestrator: prepend this block (adjust the absolute path if the repo moves),
then add the task-specific slots (Who/What/Why/Constraints/Inputs/Output
contract) per workflow.md §Prompt Design.

```text
Before doing anything else:
1. Read /home/abc/work/ai-stack/workflow/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's three questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger.
```
