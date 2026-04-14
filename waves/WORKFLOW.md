# WORKFLOW — GoBP Build Pipeline

**File:** `D:\GoBP\waves\WORKFLOW.md`
**Version:** v0.1
**Owner:** CTO Chat
**For:** Claude CLI orchestrator + Cursor builder + Qodo tester

---

## OVERVIEW

GoBP is built through a **3-tier pipeline** orchestrated by Claude CLI. Each task in each wave passes through all 3 tiers before being committed.

```
┌──────────────────────────────────────────────────────────┐
│           TIER 1 — DEV (Cursor)                          │
│           Implement code per task spec                   │
│           Output: code files + Cursor's self-test result │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│           TIER 2 — TEST (Qodo)                           │
│           Generate tests, run pytest                     │
│           Output: test files + pass/fail report          │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│           TIER 3 — AUDIT/REFACTOR (Claude CLI)           │
│           Independent review of code + tests vs Brief    │
│           Output: pass/fail decision                     │
└──────────────────────┬───────────────────────────────────┘
                       │
                  ┌────┴────┐
                  │         │
               PASS      FAIL
                  │         │
              COMMIT    ┌───┴───┐
              TASK      │       │
                     FIXABLE  MAJOR
                        │       │
                    LOOP T1  ESCALATE
                              CEO
```

---

## ACTORS

### CTO Chat (Claude Desktop) — Designer
- **Out of pipeline runtime**
- Writes Wave Briefs (this file's siblings)
- Resolves escalations from CEO
- Updates Briefs when blockers arise

### Claude CLI — Orchestrator + Tier 3 Auditor
- **Top of pipeline**
- Reads Brief
- Dispatches Cursor (Tier 1)
- Triggers Qodo (Tier 2)
- Audits result (Tier 3)
- Commits per task
- Escalates when blocked

### Cursor — Tier 1 Builder
- **Implementation only**
- Reads task spec from Brief
- Writes code per spec
- Cannot self-decide outside spec
- Reports back to Claude CLI

### Qodo — Tier 2 Tester
- **Test generation only**
- Generates tests for code Cursor wrote
- Runs pytest
- Reports results

### CEO — Escalation contact
- Out of pipeline runtime
- Handles escalations from Claude CLI
- Relays between Claude CLI and CTO Chat
- Approves git push

---

## TASK GRANULARITY (CRITICAL RULE)

**Each task in a Wave Brief = 1 git commit.**

A wave is broken into atomic tasks. Each task:
- Has a single, clear goal
- Touches a small number of files (typically 1-5)
- Can be tested independently
- Has explicit acceptance criteria
- Takes Cursor 5-30 minutes to implement

**NOT** allowed:
- Mega-tasks that touch 20+ files
- Tasks without acceptance criteria
- Tasks that can't be tested in isolation
- Wave-level commits (commit must be task-level)

**Why task-level commits:**
- Atomic rollback (one bad commit, one revert)
- Each commit verified by full pipeline (Cursor + Qodo + CLI)
- Clean git history (one task per commit)
- `git bisect` works at task granularity
- Easier debugging when something breaks later

---

## PIPELINE EXECUTION (per task)

### Step 1 — Read task

Claude CLI reads:
- Current Wave Brief
- Specific task within the brief
- Foundational docs referenced by task

If anything unclear, escalate before proceeding.

### Step 2 — Dispatch to Cursor (Tier 1)

Claude CLI runs:
```bash
cursor-agent --force --print "
WAVE <N> TASK <X>

Task spec from waves/wave_<N>_brief.md:

<paste exact task spec from brief>

Required reading before starting:
- .cursorrules
- CHARTER.md
- docs/VISION.md
- docs/ARCHITECTURE.md
- <other docs per task>

Acceptance criteria:
<paste from brief>

Use the explorer subagent before creating any new file or class.

When done, return JSON with fields:
- status: 'done' | 'failed' | 'blocked'
- files_created: [list]
- files_modified: [list]
- summary: 'short description'
- issues: [list of issues encountered]
" --output-format json
```

Cursor implements per spec, calls explorer subagent for any new creation, reports JSON back.

### Step 3 — Test (Tier 2)

Two patterns:

**Pattern A — Cursor includes Qodo in its work:**
The task spec instructs Cursor to "use Qodo to generate tests after implementation." Cursor handles Qodo internally. Claude CLI just runs pytest on output.

**Pattern B — Claude CLI dispatches Qodo separately:**
After Cursor finishes implementation:
```bash
cursor-agent --force --print "
Use Qodo to generate comprehensive pytest tests for these files:
<file_list from Cursor's output>

Tests must cover:
1. Happy path
2. Edge cases (empty input, None, max values)
3. Error paths (invalid input, missing fields)
4. Schema validation if applicable

Then run: pytest tests/<test_file> -v
Return JSON with test results.
" --output-format json
```

Default to Pattern A. Use Pattern B if Pattern A fails or task specifically requires.

After tests generated, Claude CLI runs:
```bash
pytest tests/ -v --tb=short
```

Captures output for Tier 3 audit.

### Step 4 — Audit (Tier 3)

Claude CLI itself audits. Independent perspective:

```
Read:
- Cursor's output JSON
- Files Cursor created (line by line)
- Test files Qodo generated
- pytest output
- Original Brief task spec

Check:
- [ ] Files created match spec exactly
- [ ] No extra files (scope creep)
- [ ] No files modified outside scope
- [ ] Type hints present on all functions
- [ ] Docstrings on all public functions
- [ ] No bare except clauses
- [ ] No hardcoded paths
- [ ] No forbidden imports
- [ ] Tests cover happy path + edges + errors
- [ ] All tests passing
- [ ] Schema valid (if applicable)
- [ ] Brief acceptance criteria all met

Decision:
- All checks pass → Step 5 (commit)
- Minor issues → Loop to Tier 1 with fix instructions
- Major issues → Escalate (Step 6)
```

### Step 5 — Commit task

```bash
git add <only intended files>
git status  # verify no junk staged
git commit -m "Wave <N> Task <X>: <description>

- file1.py: <change>
- file2.py: <change>
- tests/test_file1.py: created (<N> tests)

[Optional explanation]"
```

Do NOT push yet. Push happens at end of wave or per CEO instruction.

Move to next task.

### Step 6 — Escalate (only if blocked)

When stuck beyond control:

1. Stop. Do not commit.
2. Create `escalation/blocker_<timestamp>.md` with:
   - Wave + Task identifier
   - What was attempted
   - What went wrong
   - Why cannot proceed
   - Files in current state
   - Suggestion if any
3. Print clear message to terminal:
   ```
   BLOCKED — Wave N Task X
   See: escalation/blocker_<timestamp>.md
   CEO action: open Claude Desktop, paste blocker, get CTO direction
   ```
4. STOP execution.

---

## RETRY POLICY

### Cursor failure — retry up to 3 times
- 1st fail: retry with same instruction
- 2nd fail: retry with explicit fix instruction based on error
- 3rd fail: escalate

### Qodo failure — retry up to 2 times
- 1st fail: retry test generation
- 2nd fail: try Pattern B if was using A (or vice versa)
- Still fail: write tests yourself (Claude CLI), if cannot, escalate

### Test failure — retry up to 3 times
- 1st fail: send back to Cursor with fix instruction
- 2nd fail: send back to Qodo with new test instruction
- 3rd fail: escalate

### Audit failure (Tier 3) — retry up to 2 cycles
- 1st cycle: send specific issues back to appropriate tier
- 2nd cycle: same
- Still failing: escalate

**Total retries per task: 3.** After that, escalate. Do not infinite-loop.

---

## ESCALATION RESOLUTION

When CEO returns from CTO Chat:

1. CEO updates Wave Brief (if needed) — commit the update
2. CEO tells Claude CLI: "Continue from blocker_<timestamp>"
3. Claude CLI:
   - Reads escalation file
   - Reads updated Brief
   - Reads any direction from CEO
   - Resumes from failed task
   - Re-runs full pipeline (Tier 1 → 2 → 3)

If still blocked after resume, escalate again with new context.

---

## WAVE COMPLETION

When all tasks in a wave done:

1. Print summary:
   ```
   WAVE <N> COMPLETE
   Tasks: <count> done
   Commits: <count>
   Tests: <count> passing
   ```

2. Wait for CEO approval to push:
   ```
   Push to GitHub? (y/n)
   ```

3. After CEO approval:
   ```bash
   git push origin main
   ```

4. Move to next Wave Brief if exists. If no more waves, print final summary.

---

## INTER-WAVE TRANSITIONS

After a wave is pushed:
1. Read next wave brief
2. Check for any updates to foundational docs (re-read if changed)
3. Begin next wave from Task 1
4. Same pipeline applies

---

## COMMUNICATION CHANNELS

**Within pipeline (auto):**
- Claude CLI → Cursor: Bash + cursor-agent CLI
- Cursor → Claude CLI: JSON stdout
- Claude CLI → Qodo: Bash + cursor-agent CLI (Cursor invokes Qodo)
- Qodo → Claude CLI: JSON stdout
- Claude CLI → Audit: Internal

**Escalation (manual):**
- Claude CLI → CEO: Print to terminal + write blocker file
- CEO → CTO Chat: Open Claude Desktop, paste blocker
- CTO Chat → CEO: Chat response, possibly Brief update
- CEO → Claude CLI: "Continue from <blocker>"

**Approval gates (manual):**
- CEO approves git push at end of each wave
- CEO approves any deviation from Brief
- CEO approves any new dependencies

---

## CRITICAL RULES

1. **Task-level commits.** Never wave-level.
2. **No scope creep.** Brief is law.
3. **Audit is non-negotiable.** Tier 3 runs every task.
4. **Discovery before creation.** Use explorer subagent.
5. **No silent fixes.** Escalate when uncertain.
6. **No improvisation.** Follow Brief verbatim.
7. **Push only with CEO approval.** Commits accumulate, push deliberately.
8. **3 retries max per task.** Then escalate.
9. **Foundational docs are read-only.** Cannot edit without escalation.
10. **CTO Chat is the only architect.** Cursor and Claude CLI execute.

---

## FILES THIS WORKFLOW REFERENCES

**Read by all actors:**
- `CHARTER.md` — project mission
- `README.md` — overview
- `docs/VISION.md` — principles
- `docs/ARCHITECTURE.md` — system design
- `docs/SCHEMA.md` — data model
- `docs/MCP_TOOLS.md` — API contract
- `docs/INPUT_MODEL.md` — capture patterns
- `docs/IMPORT_MODEL.md` — import flow

**Read by Claude CLI orchestrator:**
- `CLAUDE.md` — Claude CLI instructions
- `waves/wave_<N>_brief.md` — current wave spec

**Read by Cursor builder:**
- `.cursorrules` — Cursor instructions
- `.cursor/agents/explorer.md` — discovery subagent
- Wave brief task being executed

**Created during pipeline:**
- `gobp/` — Python package source
- `tests/` — test files
- `escalation/blocker_*.md` — blocker reports (when escalating)

---

*WORKFLOW.md v0.1*
*Owner: CTO Chat*
*For: Claude CLI orchestrator*
