# LedgerLens AI workflow extension plan

Updated 15 October 2026: the prototype now implements personal purpose memory, read-only model tool calling, persistent conversations, constrained savings alternatives and monthly pattern reviews. See `CODE_UPDATE_2026-10-15.md` for current boundaries and `output/evidence/` for checks. The design rationale below is retained; independent model evaluation and human research remain pending.

## Priority workflows

**Personal classification memory as the foundation.** The user reports meal payments to South China University of Technology appearing under education, and electricity or air-conditioning payments to a roommate appearing as transfers. These are personal examples motivating a planned feature, not measured findings about another product. The assistant asks for the actual purpose of an unfamiliar or ambiguous payment, saves a user-confirmed example, and retrieves it for a matching later context. Approved strong matches can classify automatically. Weak, conflicting or changed contexts ask again.

Classification includes financial kind and category. Confirmed meal payments are `expense / Food`. Confirmed roommate utility payments are `expense / Utilities`, even when the source calls the payment channel a transfer. Transfers between personal accounts remain transfers excluded from spending. The original baseline expected a correct kind. The revised import and confirmation flow supports memory-based reinterpretation. The extension must retain original source labels separately while recording reviewed kind, category and decision source.

**Conversational queries with transaction evidence.** A user asks why September spending differs from August, then excludes a computer purchase. The assistant extracts the periods, selects comparison tools and explains category and transaction contributions. A follow-up retains the periods and adds an exclusion. If several purchases match, the user chooses a record. Exclusion changes the analytical scenario and does not delete the ledger record. The system recomputes totals and validates the cited IDs.

**Generated savings plans with explicit constraints.** A user asks to save CNY 6,000 in six months, keeps rent fixed and reserves at least CNY 200/month for entertainment. The assistant extracts the goal, horizon and limits, proposes alternatives and submits each to a calculation and constraint checker. A follow-up such as "Do not reduce dining" adds a locked category. Each revised plan must pass again. An infeasible result reports the remaining gap and asks which optional assumption may change. It never silently relaxes a hard constraint. Historical spending is a scenario assumption, not a guaranteed future outcome.

**Monthly review after the priority workflows.** Statistics identify major expenses, category growth, recurring merchant charges and frequent small purchases. The model explains those observations with relevant records. Recurrence alone does not prove an unwanted or duplicate subscription. Records also do not prove spending motivation. The assistant asks the user to confirm missing context.

## Personal memory design

Persistent classification memory retains confirmed purposes across imports and sessions. Temporary conversation state retains the current dates, exclusions and savings limits. This design retrieves stored examples and context for the model rather than training the model.

| Memory information | Purpose |
| --- | --- |
| Personal workspace and memory ID | Scope memory to the user's ledger |
| Counterparty and available description | Retrieve relevant examples |
| Confirmed purpose, financial kind and category | Retain the user's actual choice |
| Context and approved matching conditions | Define when future reuse applies |
| Source transaction, confirmation time and version | Explain and audit a correction |
| Enabled state and automatic-reuse permission | Support disabling or requiring review |

Amounts and frequency can support a match but do not prove purpose. A meal example must not turn every payment to the university into Food. Tuition to the same payee and an unrelated payment to the same roommate are required counterexamples. If available context is insufficient, ask the user to narrow the pattern or review the new transaction.

The proposed sequence is import with original labels, retrieve candidates, interpret context, validate approved conditions, then apply a strong approved match or ask the user. A confirmation can apply only to this transaction or also to matching future payments. Save confirmed interpretations rather than recycling unreviewed model guesses as ground truth. Show which memory supported an automatic decision. Provide inspection, editing, disabling and deletion in a memory manager. A memory change does not silently rewrite history. Batch relabeling would require a preview and separate confirmation.

## Proposed tool boundary

The table below preserves the original proposed decomposition. The implemented allowlist is `retrieve_category_memories`, `query_transactions`, `compare_periods`, `generate_savings_plans` and `monthly_review`. Savings calculation and constraint checking are internal parts of `generate_savings_plans`, rather than separate model-callable tools.

| Tool | Inputs to validate | Structured result |
| --- | --- | --- |
| `retrieve_category_memories` | Personal scope, counterparty and available context | Confirmed examples, matching conditions and source IDs |
| `query_transactions` | Explicit date range, category, selected/excluded record IDs | Records and exact totals for the permitted scope |
| `compare_periods` | Two ranges and exclusions | Period totals, category deltas, contributing record IDs |
| `calculate_savings` | Goal, horizon and proposed monthly category amounts | Monthly savings, projected savings, gap and assumptions |
| `check_constraints` | Proposed amounts, locked categories and category floors | Feasibility, individual constraint results and violations |

The model interprets requests, chooses approved tools, explains results and proposes options. Python validates arguments and approved memory conditions, runs queries and calculates money using integer fen. The application returns results to the model within a bounded tool loop. Session state preserves dates, exclusions and constraints. The model receives only necessary records and cannot execute arbitrary SQL or write directly to SQLite. The application validates numeric claims and record references. User-approved matching policies authorize automatic future classification. Uncertain classifications, memory creation or changes, and saved plans require confirmation.

The request/call/execution/result/response loop follows the [official OpenAI Function calling guide](https://developers.openai.com/api/docs/guides/function-calling), accessed 10 October 2026. The financial checks and confirmation policy are this project's proposed design.

## Development work packages

| Stage | Concrete work | Reviewable output |
| --- | --- | --- |
| 1. Requirements and data model | Interview students, separate purposes from source labels, define memory and financial schemas | User stories, memory schema and reference cases |
| 2. Personal classification memory | Store confirmations, retrieve context, validate matches, implement correction and forgetting | Correct reuse and a conflicting-purpose review |
| 3. Conversations and savings tools | Build comparison tools, session state, goal extraction and constraint checks | Queries with evidence and checked plans that support follow-ups |
| 4. Interface and monthly reviews | Build memory manager, decision provenance, pattern review and confirmation UI | Memory controls and complete workflow |
| 5. Independent evaluation and defense | Freeze reference cases, compare with baseline, test failures, rehearse | Evaluation report, failure logs, contribution records and demo |

Stages express sequence. No instructor-confirmed deadline or completed team contribution is implied. The proposed division has Chen Tianyu leading requirements, architecture, AI memory/chat/planning, core development and integration, Zhu Juncheng supporting backend/data, and Zhang Hanwen supporting interface/testing/demo. The team must agree on actual tasks and record completed work.

## Planned independent evaluation

| Measure | Evaluation method |
| --- | --- |
| Memory classification | Compare kind/category accuracy before and after a confirmed seed on new transactions. |
| Incorrect automatic labels | Report incorrect automatic labels divided by all automatic labels. Include conflicting purposes and unclear transfers. |
| Correction burden | Record repeated questions and corrections. Fewer prompts must not hide more incorrect automatic labels. |
| Source support | Check whether each spending claim cites existing records that actually support the statement. Report unsupported or missing evidence. |
| Amount consistency | Compare totals, deltas and savings with independently computed reference values. Check changed periods and exclusions across turns. |
| Constraint compliance | Verify every locked category and floor. Accept a valid plan or an explicit infeasible result. Record any silently relaxed limit. |
| Task completion | Compare the proposed assistant and current baseline on the same complete tasks, including the follow-up. Report unsupported tasks rather than omitting them. |
| Usability and operation | Observe user understanding, record response time, tool failures and recovery. Keep interview findings separate from automated case results. |

Reference cases should be labeled and held apart from prompt/rule development. For memory evaluation, give compared systems the same confirmed seed and evaluate distinct later transactions rather than the seed itself. Test meal and tuition payments to the same university, utility and unrelated payments to the same roommate, true internal transfers, changed or missing descriptions, stale/conflicting memories, and memory editing/deletion. Include ambiguous dates or purchases, contradictory limits, impossible targets, missing data, invalid tool arguments, unsupported record IDs and provider failures. Failures retain the ledger and identify the limitation. The baseline remains available with a visible mode label.

Current evidence includes 83 passing domain/HTTP checks, a complete new-workflow browser replay, and live DeepSeek synthetic smoke checks (three tool-calling questions and three contextual purpose proposals). The original baseline record remains 28 tests and 18/20 rules classifications. All these authored development examples are distinct from a held-out quality evaluation. Independent model quality and user research remain pending.
