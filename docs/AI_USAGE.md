# AI assistance disclosure and review record

Tool: OpenAI Codex in the Codex desktop application. Dates: 9–15 October 2026.

The user requested help completing a CSSE2026 Final Project, chose the AI Personal Finance Assistant option, and authorized a new implementation. Codex inspected the supplied course PDFs, wrote the initial requirements, backend, frontend, tests, evaluation scripts and English delivery materials, and ran the local verification. Actual Budget and Firefly III were consulted as related work. No source code from either repository was incorporated.

## Recorded tasks and agent changes

| Task | Produced work | Agent checks/changes | Human status |
| --- | --- | --- | --- |
| Requirements synthesis | Three stories, acceptance criteria and project scope | Compared to Project Kickoff and Lecture 01/02 | User selected topic. Detailed team review pending |
| Implementation | Python HTTP, SQLite ledger, vanilla JS UI | Exact fen arithmetic, atomic validation, duplicate identity, proposal review | Student review pending |
| Verification | Domain/HTTP suite and baseline benchmark | Tested rejection state, concurrency, rollback, schema failure, provenance | Student rerun and interpretation pending |
| Browser evidence | Real UI walkthrough and captioned recording | Corrected test synchronization after a stale status-message race | Student rehearsal pending |
| Delivery material | English report, slides, demo script | Aligned numerical claims to generated evidence | Team attribution and final acceptance pending |

Three agent-authored verification issues were found and corrected: the evaluation initially read its temporary database after the temporary directory closed, the browser check initially used a previously displayed status message to infer a new scenario had finished, and the mobile-width check compared with an expanded innerWidth rather than the requested 390-pixel viewport. The fixes capture the database comparison inside its lifetime, wait for the specific changed projection in the UI, and enforce the intended mobile width. Grid minimum width and chart labels were corrected after inspecting the full mobile screenshot. These are changes by the agent, not claimed student changes.

## Runtime AI record

The original recorded baseline did not configure a language model. On 15 October, the user supplied a DeepSeek credential and authorized continued implementation. Codex configured the key only in the ignored local `data/provider.json`, added contextual classification and bounded read-only tool calling, and verified three tool-calling requests plus three purpose proposals on synthetic temporary records. The ledger remained unchanged. This smoke check is not independent accuracy evidence.

Codex also implemented confirmed purpose memory, source-label preservation, kind corrections, memory lifecycle/versioning, persistent conversation context, exclusions with disambiguation, three checked savings styles, stale-preview rejection and monthly pattern reviews. The updated 83-test suite and two browser workflows use temporary databases and no external model calls. Final financial claims are rendered from program results; unverified model claims are discarded. Human review remains pending.

The first integration check exposed unsupported model display hints such as an irrelevant style. The adapter now discards unsupported hints rather than rendering them. A browser replay initially tried to change a transfer row to an expense-only category; the test was corrected to select the intended expense row. These are agent fixes, not student contributions.

## Student completion before submission

Record the actual model/provider if used. Describe the exact tasks delegated, code or decisions personally revised, checks personally performed, rejected AI outputs, and remaining risks. Students must own and explain the final submission. Do not replace this statement with an invented claim of independent authorship.

## 19 October goal-adventure update

At the user's request, Codex implemented the Chinese goal-adventure module, SVG scenery, mission integration, XP, badges, themes, idempotent allocation tracking and three-day weekly feedback. The work added 24 tests and an isolated real-browser journey. The full suite has 107 passing checks. Original financial records are separate from self-reported goal allocations. The implementation avoids rewarding repeated imports, repeated milestones, initial savings or passive model queries. Design benefits remain unmeasured; no student contribution or research result is inferred.
