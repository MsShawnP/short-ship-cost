# short-ship-cost — Failure Log

What was attempted that didn't work, why it didn't work, and what was
tried next.

Lower bar than DECISIONS.md — capture failures even when they didn't
produce a durable rule. The whole point: future-you (or future-Claude)
shouldn't re-attempt dead ends because the lesson got lost.

---

## Format

### YYYY-MM-DD — [One-line failure description]

**Attempted:** [What was tried]

**Why it didn't work:** [Concrete reason, not "it broke." If the
failure mode was technical, name the specific issue. If the failure
mode was scope or approach, name that.]

**What we tried instead:** [The next attempt, which may also have
failed and may have its own entry below]

**Status:** Resolved / open / abandoned

**Tags:** [keywords for future text-search — e.g., "rendering, pandoc,
quarto" or "scope, scrollytelling, decoration"]

---

## Entries

### 2026-05-07 — Strict tier priority + noise didn't produce documented channel fill targets

**Attempted:** The triage algorithm in `docs/triage-logic.md` calls for "walk the sorted queue strict-priority and apply noise" with channel fill targets at Walmart 78%, Costco 80%, Whole Foods 75%, UNFI/KeHE 70%, Regional 65%. Implemented exactly that in `scripts/run_triage.py` first pass.

**Why it didn't work:** Strict priority drove Walmart to 87%+ and starved Tier 3-4 channels to under 45%. Cranking noise (TIER_JUMP_PROB up to 30%, production_scale up to 1.85x) helped Tier 2 a little but nothing pushed UNFI/KeHE/Regional anywhere near targets. Costco specifically collapsed to 30-45% because its 9 authorized SKUs all overlap with Walmart's, and on those shared SKUs Walmart's much-larger demand swamps Costco's inside any priority-respecting allocation.

**What we tried instead:** (a) Fair-share with tier weights — made everyone uniform around 50% because Costco's small demand share is unaffected by weight differentiation. (b) Per-(sku, week) supply scaling at production_scale=1.4 — still ran 25pp under target due to bursty per-SKU per-week demand. (c) Direct target-driven allocation — for each line, ship `round(qty × (target_fill[channel] + N(0, 0.15)))`, capped at requested qty, with a 4% per-(sku, week) production_delayed event reducing some SKUs to 40% of intended. This produces channel fills within ±2.5pp of every target by construction.

**Status:** Resolved (target-driven allocation in production)

**Tags:** triage, allocation, fill-rate-targets, tier-priority, costco

### 2026-05-07 — Buffer simulation initial design didn't reproduce baseline at current fill rate

**Attempted:** First version of `scripts/cost_engine/buffer_simulation.py` lifted every line below the target rate to target, with no guard for `target ≤ current_fill`. Validation check "running at current fill should reproduce baseline within $1/dim" failed by $4.9M on lost_revenue alone.

**Why it didn't work:** The per-line lift fired even when target = current. Lines below their channel's effective rate (e.g., Regional at 63% effective) got raised toward the OVERALL current rate (73.4%), distorting the per-line distribution and shifting all downstream cost calculations.

**What we tried instead:** Short-circuited both `recover_retail_shorts` and `recover_dtc_outcomes` when `target_fill <= current_fill` so the simulation copies the orders DB but makes no modifications. Higher target scenarios (80/85/90/95%) unchanged because all are above the 73.4% current. Validation now passes.

**Status:** Resolved

**Tags:** buffer-simulation, baseline-reproduction, fill-rate, cost-engine

### 2026-05-15 — Preview screenshot tool consistently times out on this project

**Attempted:** Used `preview_screenshot` to visually verify layout changes after editing DimensionToggle and other CSS. Tried multiple times across the session — after page load, after reload, at desktop and mobile viewports.

**Why it didn't work:** The screenshot call times out after 30s every time on this project. Likely related to the page's lazy-loaded Recharts chunks or the SVG-heavy flow-split chart. Same issue observed in prior sessions.

**What we tried instead:** Used `preview_eval` to inspect computed styles (grid columns, chip widths, alignment) and `preview_snapshot` for accessibility tree structure. Both work reliably and provide sufficient verification for CSS layout changes.

**Status:** Open (environment limitation, not a code issue)

**Tags:** preview-tool, screenshot, timeout, verification, css-layout

### 2026-05-07 — Costco demand exceeded total brand supply on some authorized low-velocity SKUs

**Attempted:** The order generator uses velocity-weighted SKU sampling without replacement within each retailer's authorized SKU set. Costco only has 9 authorized SKUs and orders 6-15 lines per PO with case quantities of 30-300, so almost every Costco order touches every authorized SKU with large quantities.

**Why it didn't work:** Costco's auth list includes a few low-velocity SKUs (CHP-0014 rank 66, CHP-0037 rank 77). Costco's generated 2-year demand on CHP-0014 was 13× the entire brand's 2-year supply for that SKU. Real Costco wouldn't carry low-velocity SKUs at that volume — the generator's velocity weighting wasn't aggressive enough at filtering when the auth set is small.

**What we tried instead:** Didn't roll back to the generator (sub-task 4 was already running and re-tuning was disruptive). Instead acknowledged in the cost engine's triage that strict priority can't repair this and switched to direct target-driven allocation, which sidesteps the per-SKU competition. Documented the underlying generator artifact in commit messages and `docs/cost-engine-docs.md` known-limitations section.

**Status:** Worked-around, not fixed at the source

**Tags:** generator, sku-selection, costco, velocity-weighting

### 2026-05-08 — Section 1 chart form took five iterations to land on flow-split

**Attempted:** Started with a Recharts waterfall (stacked bars + invisible spacers) showing all 8 dimensions cumulatively building to the $25.6M total. Then a two-tier layout splitting "the gap you knew about" (lost revenue) from "the costs you didn't" (cascading). Then a single horizontal stacked bar with all 8 dimensions, with sequential blue palette and an outside legend. Then a vertical stacked bar with y-axis dollar scale and fan-out leader lines for clustered small dimensions.

**Why it didn't work:** Lost revenue is ~73% of the total and deauthorization is another ~23%, so the remaining 6 dimensions live in the last few pixels of any proportional chart. Waterfall: the 90%+ dim was so dominant the smaller bars looked like noise. Two-tier: visually separated lost revenue from cascading costs but felt like two disconnected charts. Horizontal stacked bar: thin slivers on the right edge weren't readable even with an outside legend. Vertical stack: leader-line fan-out for sub-pixel segments was inherently chaotic.

**What we tried instead:** A custom-SVG flow-split: a single navy "Total" block on the left, eight right-side blocks (each at minimum 20px height for readability), and Sankey-style curves connecting them. Block heights aren't strictly proportional for the smallest dimensions — accepted as an honest tradeoff and footnoted. Click-to-pin shows exact values. This is what shipped.

**Status:** Resolved (flow-split is the production form)

**Tags:** visualization, iteration, section-1, flow-chart, sankey

### 2026-05-08 — CSS modules hash format isn't stable enough for cross-module print rules

**Attempted:** Used `[class*='RetailerDrilldown_tableBlock']` attribute selectors in `App.css` print rules to force "Top products by cost" onto a new printed page, expecting CSS modules to namespace-mangle classes as `ComponentName_localName_hash`.

**Why it didn't work:** Vite's CSS modules hash format isn't reliably `ComponentName_localName_hash`. The selectors didn't match in production builds, so the page-break rule silently did nothing. Tested in print preview, still no break — flagged by user after second attempt didn't take.

**What we tried instead:** Added a global `.print-break-before` class (declared in `App.css`, not module-scoped) and applied it directly via JSX: `className={`${styles.tableBlock} print-break-before`}`. Same approach for the staircase-block grouping in BufferSimulation: explicit class names in `print-*` namespace. Print page breaks now apply reliably.

**Status:** Resolved

**Tags:** print-css, css-modules, vite, page-break

### 2026-05-08 — Buffer scenario deauth recalc on threshold change is approximate

**Attempted:** When the user changes the distributor fill rate threshold via the parameter panel, ideally the buffer simulation's deauth values for each scenario (80/85/90/95% fill) should be recomputed exactly: which events get avoided at each scenario depends on the new threshold. Original Python simulation has per-scenario per-event recovery flags (`buffer_deauth_recovery` table).

**Why it didn't work:** The buffer simulation requires per-event monthly fill data and the per-scenario simulated retail/distributor lift, neither of which is in the JSON we ship to the browser. Replicating it would either require shipping the orders DB (22 MB, not viable) or pre-computing buffer scenarios for every possible threshold value.

**What we tried instead:** Approximate via ratio scaling: `deauth_scale = filtered_total / baseline_total` where filtered = events that still trigger at the new threshold. Each scenario's by_dimension deauth value is multiplied by this scale. This preserves the cliff shape qualitatively but isn't exactly right when the threshold change moves the cliff position. Documented as a known approximation in code comments and accepted.

**Status:** Worked-around, not fixed (would require additional pre-computed data)

**Tags:** cost-engine, approximations, buffer-simulation, parameter-panel, deauthorization

### 2026-06-14 — Docker container name mismatch during platform rebuild

**Attempted:** Connected to local Postgres replica using container name `cinderhaven-postgres` in the rebuild script.

**Why it didn't work:** The actual Docker container name is `cinderhaven-data-platform-postgres-1` (Docker Compose names containers as `{project}-{service}-{instance}`). The shorter name was a guess.

**What we tried instead:** Ran `docker ps -a` to find the actual container name. Minor issue, fixed in seconds.

**Status:** Resolved

**Tags:** docker, container-name, postgres, rebuild

---

### 2026-09-02 — gitleaks silently falls back to default rules when `--config` points at a missing file

**Attempted:** Assumed that because otif-blind-spot and contract-to-cash both
pass `args: ["--config", ".gitleaks.toml"]` in `.pre-commit-config.yaml`, a
missing `.gitleaks.toml` would make the hook fail loudly and be noticed.

**Why it didn't work:** It doesn't fail. Ran `gitleaks protect --staged --config
.gitleaks.toml` in otif-blind-spot, where no such file exists: exit 0, "no leaks
found", no warning that the config was unreadable. gitleaks quietly uses its
default ruleset. Both repos have therefore been scanning with defaults only —
the same ruleset that missed the keyword-form DSN in this repo for three months
— while presenting a green hook. False assurance one level up from the original
blind spot.

**What we tried instead:** Nothing yet. Recorded as a tracked sibling in
HANDOFF.md: copy this repo's `.gitleaks.toml` into both. Latent rather than
live — neither repo hardcodes a credential today, both are on `DATABASE_URL`.

**Status:** Open

**Tags:** gitleaks, pre-commit, secrets, config, false-negative, sibling-surface

---

### 2026-09-02 — Over-literal grep produced a false "`.env` not gitignored" finding

**Attempted:** Checked `.env` coverage across three repos with
`grep -c '^\.env$' .gitignore`.

**Why it didn't work:** Anchored on an exact line match. contract-to-cash
ignores env files via `.env*`, which the pattern missed, so the check reported
zero and nearly went into the summary as a live secret-exposure finding in a
public repo. The audit was wrong, not the repo.

**What we tried instead:** Re-ran as `grep -nE "^!?\.env|\.env"` and printed
the matched lines rather than a count. Reading the actual patterns showed all
three repos covered.

**Status:** Resolved

**Tags:** grep, gitignore, false-positive, audit-method, verification

---

### 2026-09-02 — Recursive Bash grep over the repo timed out

**Attempted:** `grep -rniIl -E "password|passwd|..."` from the Bash tool to find
credential keywords across the working tree.

**Why it didn't work:** Exceeded the 120s tool timeout on this tree under Git
Bash on Windows and was backgrounded, stalling the search.

**What we tried instead:** The ripgrep-backed Grep tool, which returned the three
matching files immediately.

**Status:** Resolved

**Tags:** grep, ripgrep, windows, tooling, performance

### 2026-09-02 — Output redaction masked a real hardcoded password and produced a false "clean" audit verdict

**Attempted:** Swept all three DB-backed repos for the same hardcoded-DSN
defect, inspecting each connection site through
`sed -E 's#://[^@]*@#://<REDACTED>@#g'` so no credential could reach
terminal output.

**Why it didn't work:** The mask replaced everything between `://` and `@`,
so a literal password and a `{pw}` interpolation rendered as the same
string. contract-to-cash's `scripts/db.py:32` showed as
`postgresql://<REDACTED>@localhost:5432/cinderhaven`, the line above it read
`pw = os.environ["POSTGRES_PASSWORD"]`, and the obvious inference -- that
the masked span was `{pw}` -- was wrong. It was a literal. The sweep was
recorded as "checked, no hardcode" and committed to HANDOFF.md that way.

**What we tried instead:** Classified the masked span instead of reading it:
matched the URL regex, then printed only `len(slot)` and its character
shape (`re.sub(r'[A-Za-z]','a',slot)`). Shape came back as 8 plain alpha
characters with no braces, which an interpolation cannot be. Confirmed by
counting `pw` occurrences in the file -- exactly one, its own assignment.

**Lesson:** A redaction that collapses distinct inputs to the same output is
not safe for auditing, only for display. When the question is *what shape is
this value*, redact by reporting derived properties (length, character
class, brace presence) rather than by substituting a constant. Also: the
scanner found this, the manual sweep did not -- install the tool before
trusting the sweep.

**Status:** Resolved -- b91bd7b removed the credential; both sibling repos
now carry `.gitleaks.toml`.

**Tags:** redaction, audit-method, false-negative, secrets, gitleaks,
sibling-surface, verification

### 2026-09-03 — `sed -i` stripped CRLF and I blamed `.gitattributes` for the resulting whole-file diff

**Attempted:** `sed -i 's/branches: \[master\]/branches: [main]/' .github/workflows/ci.yml`
to change two lines. `git diff --cached` reported 24 insertions, 24
deletions -- the entire file.

**Why it didn't work:** `sed -i` in Git Bash rewrites the file with LF
endings. `ci.yml` was the only workflow blob stored with CRLF, so every
line differed. I diagnosed it as `* text=auto` in `.gitattributes`
renormalizing the file on commit, wrote that explanation into the commit
message, and merged it to `main`.

**What we tried instead:** Nothing at the time -- the diff was accepted as
unavoidable. Later, appending the HANDOFF entry with `printf '%s\r\n'`
produced a clean 25-line diff on a file with the identical `text=auto`
attribute. That disproved the renormalization theory: `text=auto` leaves a
CRLF-stored file alone when the incoming content is also CRLF.

**Lesson:** On Windows, `sed -i` is not line-ending-neutral. Match the
stored endings (`git show HEAD:<file> | file -`) before editing, and use
`printf '%s\r\n'` to append to a CRLF file. And do not write a
causal explanation into a commit message without testing it -- the wrong
one is now permanent in `cc1b620`.

**Status:** Resolved for method; the incorrect commit message stands on
`main` and was corrected in HANDOFF.md rather than by rewriting history.

**Tags:** crlf, line-endings, sed, gitattributes, windows, git-bash,
commit-message, unverified-claim

---

### 2026-09-03 — Diagnosed a stuck interactive prompt as a permissions problem for two turns

**Attempted:** Handed the user four cleanup commands to run in their
terminal (`worktree remove`, `push origin --delete`, `branch -D`,
`remote prune`). When they reported nothing worked, I inspected repo state,
found all branches intact, and concluded the commands had not been run.

**Why it didn't work:** `git worktree remove` had hit
`Deletion of directory ... failed. Should I try again? (y/n)` and was
waiting on stdin. Every subsequent command the user typed was consumed as
an answer to that prompt and echoed back
`Sorry, I did not understand your answer`. Repo state was correct evidence
of the symptom and useless for the cause. The directory could not be
unlinked because this session's shell held it as cwd -- the harness resets
cwd into the worktree after every command.

**What we tried instead:** Read the terminal with the `read_terminal` tool.
The prompt loop and the `Permission denied` cause were both visible in the
first 60 lines.

**Lesson:** When the user says a command did not work, read their terminal
before inferring from repo or filesystem state. Also: never hand a user a
`git worktree remove` for a worktree the current session is running inside
-- it cannot succeed, and it blocks on an interactive retry prompt.

**Status:** Resolved -- user typed `n`, terminal freed, cleanup completed
from this session instead.

**Tags:** interactive-prompt, stdin, worktree, diagnosis, read-terminal,
windows, file-lock

---

### 2026-09-03 — Bundling a read-only check with a mutation got the whole Bash call denied

**Attempted:** One command combining `ls-remote` verification,
`git remote prune origin`, and a directory listing.

**Why it didn't work:** The auto-mode classifier evaluates the whole
command string. `remote prune` tripped it, so the verification output was
lost with it.

**What we tried instead:** Split into separate calls. The read-only halves
ran immediately.

**Lesson:** Keep verification and mutation in separate tool calls. A denial
costs the entire call, not just the offending clause. Related: the same
`push origin --delete` was denied twice and succeeded on the third attempt
after explicit user authorization -- the classifier reads conversation
context, so re-asking the user is the unblock, not rephrasing the command.

**Status:** Resolved.

**Tags:** classifier, permissions, tool-calls, verification, batching

---
