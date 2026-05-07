---
description: End-of-session wrap. Structured summary, updates HANDOFF/FAILURES/DECISIONS, commits with full journal in commit body.
---

End-of-session protocol. Do these in order. Do not skip steps.

## Step 1: Session summary

Before writing anything to files, produce a structured summary of
this session. Show it to the user for review.

Format:

---
**Session summary — [date, time]**

**Starting point:** Where we began this session. One or two lines.
Pull from the previous HANDOFF.md entry if available.

**What we did:** The work performed this session. Specific, not
"worked on the report." Use bullets if multiple distinct things.

**What worked:** Approaches that succeeded. Why they worked, if
non-obvious.

**What didn't work:** Approaches tried that failed or were abandoned.
Why. What was tried instead. Even small failures count — they're the
highest-value capture.

**Surprises:** Anything unexpected. Code behaving differently than
predicted, results that didn't match assumptions, edge cases
discovered. This is where future-you finds intuition.

**State now:** What's working, what's broken, what's untouched.
Concrete, not vague.

**Tomorrow's starting point:** What the next session should pick up.
Specific enough that fresh-Claude can act on it without asking.
---

After producing the summary, ask: "Does this summary match what
actually happened? Anything to add, remove, or correct?"

Wait for confirmation or edits before continuing.

## Step 2: Update HANDOFF.md

Append a new entry to HANDOFF.md based on the confirmed summary.
Format:

## YYYY-MM-DD HH:MM

**Started from:** [Starting point line]

**Did:** [What we did, condensed]

**State:** [State now]

**Next:** [Tomorrow's starting point]

(Keep this entry compact. The full summary is captured in the commit
message; HANDOFF.md is the at-a-glance status.)

## Step 3: Update FAILURES.md

For each item in "What didn't work" from the summary, ask the user:
"This failure looks worth capturing in FAILURES.md. Add it?"

If yes, append using the FAILURES.md format. Confirm tags before
saving.

If the user says no or skip, move on. Do not push.

## Step 4: Decision check

Review the session for any candidates for DECISIONS.md. A change is
a DECISION (not just a log entry) if any of these apply:

- It establishes a rule that should hold across future sessions
- It rejects an alternative that someone might reasonably try again
- It defines an anti-instruction
- It commits to a convention, format, or standard
- Reversing it later would require explanation

For each candidate, ask the user one at a time. Format:

> This session involved [brief description]. This looks like a
> durable decision because [reason — points to the criteria above].
>
> Add to DECISIONS.md? (yes / no / not yet)
>
> If yes, proposed entry:
>
> ### [date] — [one-line decision]
> - **Why:** [reasoning]
> - **Scope:** [what it applies to]
> - **Do not:** [anti-instruction, if applicable]

Rules:
- Ask one candidate at a time. Do not batch.
- Maximum three candidates per session.
- If the user says "not yet," note this in the HANDOFF entry and
  move on.
- If the user says "no," do not raise this candidate again unless
  the user brings it up.

## Step 5: PLAN.md update

If any tasks in PLAN.md were completed this session, mark them
complete. If the entire current arc is done, ask the user whether
to archive it and start a new arc.

## Step 6: Commit

After all file updates are confirmed:

1. Run `git status` to confirm what's changed.
2. Run `git add -A` to stage all modified and new files.
3. Run `git commit` with a multi-line message:

   ```
   wrap: <one-line session headline>

   <full session summary from Step 1>
   ```

   The detailed summary in the commit body means the journal is
   permanently captured in git history, searchable via
   `git log --grep=<term>`, even if HANDOFF.md gets rotated.

4. Report back the commit hash, files changed, and the "Next" line
   so the user can see what's ready for tomorrow.

## Step 7: Tag suggestion (if applicable)

If this session reached a meaningful milestone (deliverable rendered,
arc completed, version ready to share), suggest a tag name.

Do not create the tag automatically. Suggest it; let the user decide.

## Rules

- Do not skip the user-confirmation step on the summary. The summary
  drives everything else.
- If the user says "skip the summary, just commit," do that — but
  HANDOFF.md still gets a minimal entry.
- Do not push to remote. Local commit only.
- If git operations fail, stop and report the error. Do not attempt
  to fix automatically.
