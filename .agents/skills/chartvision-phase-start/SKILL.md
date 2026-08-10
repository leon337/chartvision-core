---
name: chartvision-phase-start
description: Start or resume a ChartVision Core roadmap phase. Use before planning or implementing any phase, when opening a dedicated phase chat, or when confirming whether a requested phase is authorized. Do not use to close a phase or to implement feature code.
---

# ChartVision Phase Start

Use this skill before any implementation work for a ChartVision Core roadmap phase.

## Objective

Reconstruct the real project context from the repository, verify that the requested phase is actually authorized, and produce a concise Phase Brief before code changes begin.

This skill performs **inspection and authorization only**. It must not implement feature code.

## 1. Confirm repository

Verify that the working repository is `leon337/chartvision-core` or an authorized checkout of that repository.

If the repository cannot be confirmed, return `PHASE_START = BLOCKED`.

## 2. Read the persistent memory

Read in this exact order:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/SCOPE.md`
4. `docs/ROADMAP.md`
5. `docs/DECISIONS.md`
6. `docs/CONTINUITY_PROTOCOL.md`
7. documentation specific to the currently authorized phase
8. `docs/CHATGPT_PROJECT_INSTRUCTIONS.md` when present

Do not infer current state from prior conversation history.

## 3. Inspect real repository state

Collect, when available:

- current branch;
- current HEAD SHA;
- working-tree status;
- latest CI status for the relevant HEAD;
- master roadmap issue state;
- relevant open PRs/issues;
- last verified PASS evidence.

If a source cannot be verified, report it as `UNKNOWN`. Never invent a result.

## 4. Verify consistency

Compare:

- requested phase;
- phase marked PASS in `PROJECT_STATE.md`;
- next authorized phase;
- `ROADMAP.md` status;
- master issue status;
- real code/CI evidence.

### BLOCKED conditions

Return `PHASE_START = BLOCKED` and do not implement when any of the following occurs:

- requested phase is not the next authorized phase;
- official documents contradict one another;
- current HEAD has a known failing CI that invalidates the previous PASS;
- an unresolved blocker explicitly prevents the phase;
- repository identity cannot be confirmed.

### NEEDS_VERIFICATION condition

Return `PHASE_START = NEEDS_VERIFICATION` when a critical source required to authorize the phase cannot be accessed or verified.

Do not silently convert unknown information into success.

## 5. Scope lock

Extract only the current phase requirements.

Explicitly list:

- objective;
- allowed implementation;
- prohibited implementation;
- acceptance criteria;
- required tests;
- dependencies from earlier phases;
- known risks/blockers.

Do not add useful-looking functionality from later phases.

## 6. Required output — Phase Brief

Produce exactly this operational structure:

```text
PHASE_START = READY | NEEDS_VERIFICATION | BLOCKED

PHASE:
OBJECTIVE:
CURRENT_BRANCH:
HEAD:
WORKTREE:
LATEST_VERIFIED_PASS:
CI:
MASTER_ISSUE:
AUTHORIZED_SCOPE:
OUT_OF_SCOPE:
ACCEPTANCE_CRITERIA:
REQUIRED_TESTS:
BLOCKERS:
AUTHORIZED_NEXT_ACTION:
```

If `READY`, `AUTHORIZED_NEXT_ACTION` must describe only the first bounded task of the authorized phase.

If `BLOCKED` or `NEEDS_VERIFICATION`, state the exact evidence or correction required before implementation.

## 7. Hard rules

- Do not modify feature code while running this skill.
- Do not advance a roadmap status.
- Do not mark a phase PASS.
- Do not reinterpret the scope.
- GitHub/repository evidence wins over chat memory.
- If documents conflict, stop and correct governance before implementation.
