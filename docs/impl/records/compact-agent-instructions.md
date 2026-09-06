# Compact Agent Instructions

## Task

- Id: `compact-agent-instructions` (ad hoc); capability: `project-foundation`.
- State: CI-blocked by existing failures; requested instruction edits and review are present.
  Review owner: this documentation review; no product implementation acceptance.
- Context: existing dirty documentation preserved; no production changes requested.

Full user request, with only line wrapping added:

> You have updated AGENTS.md with ## Small-task execution and audit handoff, and the file grows
> significantly. Please analyze AGENTS.md and related instructions, and estimate whether the 
> weaker reasoning budget or old model can follow the instructions. Make them as laconic as 
> possible because the > context window of the old model is small, so we will not have context
> for the code task

Amendments: none. The subsequent `continue` resumes this scope.

## Decisions and evidence

Baseline snapshots and measurements: `.data/instruction-review/20260905/before/` and
`counts-before.json`. AGENTS contained 1,517 words; the workflow and record template added 1,796.
The tool adapters already contain only a link to AGENTS and need no change.

The edit removes duplicated completion loops and unconditional loading of planning/review details.
AGENTS now has guardrails, one ordered task cycle and three conditional routes. The workflow,
record template and specification's development-integrity section are also shorter. README and
the contributor guide no longer direct normal tasks to preload the entire workflow. Prior wording
edits in the codebase audit record were preserved; only two trailing spaces there were removed.

| Instruction | Words before | Words after | Lines before/after |
| --- | --- | --- | --- |
| AGENTS | 1517 | 501 | 169 / 53 |
| Planning workflow | 1288 | 757 | 156 / 96 |
| Record template | 508 | 237 | 61 / 40 |

Counts use whitespace splitting, not a model tokenizer. AGENTS is 67% shorter by words; the three
files together are 55% shorter. Normal AGENTS-plus-template reading is 738 words, before task/code/
spec evidence, versus 2,025 previously. Conditional planning instructions are additional when needed.

Estimate: explicit steps and fewer repeated conditions should be easier for a lower-budget model
to follow. This is a structural assessment, not measured model compliance. The remaining vulnerable
steps are checking prerequisites and matching every gate to actual evidence; those remain explicit
and retain the existing future enforcement task. No model was invoked for a benchmark.

## Rule retention review

| Requirement / scenario | Retained location and manual check |
| --- | --- |
| Scope, Git, Python/uv, typing, paths/secrets, dependency ownership | AGENTS guardrails; no permission or coding restriction removed |
| Module layout, shared policy, logging/constants, shell prefix, artifact roots, ASCII | AGENTS guardrails; specification retains refactoring boundaries |
| Existing implementation task | Task cycle: bounded scope, prerequisite check, full snapshot, regression tests and required CI |
| Interrupted or failed task | Task cycle and template: honest results, remaining gates/next action, task stays open |
| Task/capability edit | Conditional planning route: all required fields, lane/status rules, registry order/evaluation and shipped links |
| Milestone/refactor concern | Conditional review route: one note owner, separate blocking repair, checkpoint decision and explicit proof/human gates |
| Completion | Current/index/dependency links, permanent original/amended scope, gate evidence, counts, status and resource cleanup |

This review checked the old rules against the new locations and walked the listed scenarios. It
does not establish that a future agent will follow them or that record enforcement already exists.

## Acceptance and handoff

| Check | Result / evidence |
| --- | --- |
| Rule comparison and conditional reading paths | Manual review above; baseline/final snapshots and `counts-before.json`/`counts-after.json` in the audit artifact directory |
| `make lint-md DATA_DIR=.data` | Final result in `lint-md.log`; Markdown and relative links checked |
| `make -k ci DATA_DIR=.data` | `ci.log`: 168 tests pass; typing, shell lint, documentation links and spec-plan integrity pass; baseline format/import and Radon failures persist |
| `make plan-status DATA_DIR=.data` and plan snapshot comparison | 93 tasks before/after, 82 agent and 11 human; plan bytes unchanged this turn; no capability moved |
| `git diff --check` and final scope review | Whitespace/ASCII checked; no source, test, dependency or runtime changes |

The CI blockers were owned by the
[quality baseline repair](restore-quality-gate-baseline.md), which has since resolved them; at the
time of this record the Radon failure prevented the following cognitive-complexity subcheck.
No failed or unrun gate is treated as passed. Full `make quality` and model/CUDA/service runs
were not performed. No process or service remains from
this change. No new repair task or capability was needed; this record is not removed from the plan.

Current result: [Governance](../current/governance.md#one-rules-source). Audit notes: none identified
for the compact instructions after the retention review. Prior code findings keep their existing
owners; no duplicate audit backlog was created.
