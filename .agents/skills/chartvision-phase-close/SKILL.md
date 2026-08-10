---
name: chartvision-phase-close
description: Validate and close the currently authorized ChartVision Core roadmap phase after implementation. Use when work appears complete and before marking a phase PASS or opening the next phase. Do not use to start a phase or bypass missing tests, CI, documentation, or roadmap evidence.
---

# ChartVision Phase Close

Use this skill only after the implementation work for the current authorized phase is believed to be complete.

## Objective

Prove whether the phase satisfies its Definition of Done, persist the final state, and authorize the next phase only when all evidence is complete.

A phase is not complete because code exists or a command ran successfully.

## 1. Reload official state

Before evaluating completion, read:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/SCOPE.md`
4. `docs/ROADMAP.md`
5. `docs/DECISIONS.md`
6. `docs/CONTINUITY_PROTOCOL.md`
7. documentation specific to the current phase
8. `docs/CHATGPT_PROJECT_INSTRUCTIONS.md` when present

Then inspect branch, HEAD, diff, CI, relevant issues and PRs.

## 2. Confirm the phase being closed

Verify that the phase being evaluated is the currently authorized phase.

If another phase is requested, return `PHASE_CLOSE = BLOCKED`.

## 3. Review implementation scope

Inspect the actual diff/code and confirm:

- every required deliverable exists;
- no required behavior is only a placeholder;
- no later-phase functionality was introduced;
- frozen stack and architecture decisions were respected;
- no prohibited integration was added;
- no hidden future leakage or Ground Truth violation was introduced.

Any material scope creep is a FAIL until corrected or explicitly approved through `DECISIONS.md` and affected scope documents.

## 4. Execute and verify tests

Run the tests required by the current phase and relevant regression checks.

Record exact commands and results.

A test that was not run must be reported as `NOT RUN`, never assumed to pass.

## 5. Verify CI

Verify CI for the actual HEAD/PR being closed.

A phase cannot receive PASS while required CI is failing, pending without justification, or unverifiable.

If CI access is unavailable, return `PHASE_CLOSE = BLOCKED` with the required verification action.

## 6. Compare against acceptance criteria

Evaluate every acceptance criterion from `ROADMAP.md` and phase documentation individually.

Use only:

- `PASS` — evidence proves the criterion;
- `FAIL` — evidence disproves or does not satisfy it;
- `BLOCKED` — required evidence cannot currently be obtained.

Do not use optimistic interpretation.

## 7. Persist memory before PASS

Before declaring the phase closed, update as applicable:

- phase-specific documentation;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- `docs/DECISIONS.md` for any newly approved architectural decision;
- master roadmap issue `#1`;
- relevant phase issue/PR notes when they exist.

Persist:

- implemented scope;
- files/components changed;
- tests executed;
- test results;
- commit/PR/HEAD;
- CI result;
- acceptance evidence;
- limitations/known risks;
- decisions made;
- next phase authorized.

If the master issue cannot be updated with available capabilities, the close remains `BLOCKED`; provide the exact pending update instead of claiming PASS.

## 8. Next-phase rule

Closing one phase may authorize only the immediately following roadmap phase.

Do not implement or begin the next phase in the same close operation.

The next phase must start in its own dedicated chat/session and run `chartvision-phase-start` again.

## 9. Required output — Phase Closure Report

```text
PHASE_CLOSE = PASS | FAIL | BLOCKED

PHASE:
HEAD:
IMPLEMENTATION_REVIEW:
SCOPE_REVIEW:
TESTS:
CI:
ACCEPTANCE_CRITERIA:
REGRESSIONS:
DOCUMENTATION_UPDATED:
ROADMAP_UPDATED:
PROJECT_STATE_UPDATED:
MASTER_ISSUE_UPDATED:
DECISIONS_UPDATED:
KNOWN_LIMITATIONS:
NEXT_PHASE_AUTHORIZED:
HANDOFF:
```

### PASS

Allowed only when all mandatory items are verified and persistent memory is updated.

### FAIL

Use when implementation, tests, scope or acceptance criteria are not satisfied. Stay in the same phase and correct the failures.

### BLOCKED

Use when required evidence or a mandatory persistence action cannot be completed. Do not mark the phase PASS.

## 10. Hard rules

- Never mark PASS without evidence.
- Never skip required tests.
- Never hide a failing check.
- Never change historical analysis/evidence to make a criterion pass.
- Never authorize more than the immediate next phase.
- GitHub/repository state is the final source of truth.
