# LedgerLens code update — 15 October 2026

The prototype now connects confirmed personal classification memory, financial conversations, checked savings alternatives and monthly reviews. This records Codex-authored work, not completed human contributions. Chen Tianyu remains the proposed project lead/main developer, with Zhu Juncheng supporting data/backend and Zhang Hanwen supporting frontend/testing/demo.

| Capability | Implemented behavior | Boundary |
| --- | --- | --- |
| 分类记忆 | Confirm kind/category; save purpose, context and provenance; approve reuse; edit, version, disable, delete | Exact normalized payee and substring purpose conditions; no automatic semantic guess |
| Source preservation | Original kind/category, counterparty, note, corrected labels and memory version | Project CSV format; no native WeChat/Alipay export adapter |
| Multi-turn analysis | Month comparison, category changes, evidence IDs, exclusions and persisted context | Ambiguous payments ask for an ID; ambiguous years require YYYY-MM |
| Savings alternatives | Three strategies with fixed categories, floors and explicit gaps | Historical means and default cut caps are assumptions |
| Plan saving | Preview, inspect budgets and explicitly select | Recomputed and rejected if ledger revision changed |
| Monthly review | Category changes, repeated payees/descriptions and small-payment totals | Does not infer motivation or cancel subscriptions |
| DeepSeek | HTTPS tool calling and context-based purpose proposals | Chat opt-in; labeled local fallback |

The model selects read-only tools and may identify computed categories/options to focus on. Python renders monetary explanations from validated results, discarding unverified free-form numeric claims, citations and unsupported display hints. This intentionally limits free-form explanation. Previously stated and locally recognized planning limits are checked before accepting model parameters.

The allowlist is `query_transactions`, `compare_periods`, `generate_savings_plans`, `monthly_review`, and `retrieve_category_memories`. Category-budget calculation and constraint checks are internal to the savings tool. There are no write or arbitrary SQL tools. Each question allows at most three response rounds and four tool executions. Model failures do not persist speculative tool context. Money uses integer fen after Decimal validation and explicit rounding.

A saved user policy authorizes future automatic classification. First confirmation, memory changes and plan selection use explicit UI actions. Quick category edits do not create memory. Conflicting matches, review-only rules, different-purpose signals and missing context require review. Original import identity survives financial-kind correction. Memory edits/deletion preserve historical labels and audit records.

Startup adds schema/columns while retaining IDs, amounts, budgets, audit history and earlier manual scenarios. Private provider configuration loads only at app startup, not in unit tests. `FINANCE_AI_DISABLE=1` forces local-only operation. Credentials and personal databases are excluded from the archive and browser state.

The current suite has 83 passing tests. Original 28-test evidence is archived under `output/evidence/baseline-20261009/`. The original baseline remains 18/20 authored synthetic rule labels and 9/9 authored grounded questions. New Edge browser replay covers the complete workflow and 390px mobile layout. Live DeepSeek smoke checks passed three tool-calling requests and three contextual classifications without ledger writes. These were development examples, not independent accuracy or user-study evidence.

Remaining work includes independent held-out evaluation, real-user interviews, native payment export importers, broader semantic/language coverage and team review. Existing proposal slides, scripts, report PDF and baseline video remain historical artifacts. Update final-defense materials and record a new demonstration after accepting the implementation. Actual human contributions must be recorded by the students.

Protocol documentation checked 15 October 2026: [DeepSeek tool calls](https://api-docs.deepseek.com/guides/tool_calls/) and [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling). Memory approval, arithmetic and confirmation policies are project-specific code.

The later Chinese UI revision localizes navigation, category labels, suggestions, errors, memory controls, scenarios, financial answers and readable audit entries. CSV templates and exports support Chinese headers. The internal category IDs and original descriptions/purposes are preserved; exporting and reimporting existing records does not create new identities.
