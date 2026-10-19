# LedgerLens
## AI Personal Finance Assistant

CSSE2026 - Comprehensive Design of Computer Science and Software Engineering

Technical report - 9 October 2026

Team identity and member IDs have not been supplied. This initial implementation and report used substantial OpenAI Codex assistance. Actual team review and contributions must be recorded before submission.

### Abstract
LedgerLens is a local full-stack prototype for students who want to organize spending records and test a savings goal. A browser interface connects to a Python HTTP backend and SQLite database. The complete workflow imports transactions, validates and de-duplicates records, provides an overview with source links, allows classification corrections, compares savings scenarios and monitors user-defined budgets. Exact integer-fen calculations produce all monetary results. Optional model integration proposes a category and requires human review before persistence. The delivered baseline uses explicit keyword rules and deterministic tool-based questions and answers. Twenty-eight automated domain and HTTP tests pass. A 20-item synthetic classification sample yields 18 correct labels, and nine authored grounded-Q&A cases pass. Live model quality, representative user performance and production deployment remain outside the evidence. The submission includes repeatable checks, an English-captioned system recording, presentation files and an AI assistance disclosure.

[[SCREENSHOT]]

Figure 1. Browser interface after importing 30 synthetic records. All values shown derive from the local ledger.

---PAGE---
# 1. Problem, requirements and related work

### Problem and target users
A student receives a monthly allowance and records purchases across several exports. A total-spending number alone does not explain which records contribute to it or whether reducing a category would help a savings goal. LedgerLens focuses on one user with CNY transaction data and one inspectable workflow. No interviews or user study were performed. The user need is a project assumption derived from the supplied finance-assistant brief [1].

### Core user stories
| ID | User story | Acceptance evidence |
| --- | --- | --- |
| US1 | As a student, I import records and correct their categories so I can inspect a reliable spending overview. | 30-row import, repeated import, atomic rejection and human edit checks |
| US2 | As a student, I compare a savings target with category reductions so I can understand a feasible monthly change. | Six-month and four-month expected-value tests and browser replay |
| US3 | As a student, I inspect record-grounded answers and budget alerts so I can trace each conclusion. | Source-ID sums, supported/refused questions and budget overrun checks |

The baseline includes CSV input, CNY amounts, expenses/income/transfers, persisted category correction, charts, a saved scenario, in-app budget alerts and a constrained model-proposal boundary. It excludes bank synchronization, investment recommendations, receipts, multiple currencies and shared accounts. Up to 5,000 rows and 2 MB are allowed per import. No overall ledger-size or latency service-level guarantee was measured.

### Related work and project choice
Actual Budget describes a local-first personal-finance application with synchronization and budgeting features [4]. Firefly III describes a self-hosted personal-finance manager [5]. These are established alternatives for everyday financial organization. We reviewed their public repositories to compare scope. No implementation code or assets were copied from them. LedgerLens chooses a smaller inspectable implementation centered on record provenance, explicit scenario assumptions and reviewed category proposals. This is a course scope decision, not a claim that its features are superior or novel.

The final requirements also call for a runnable system, failure handling, design decisions, verification, AI evaluation or AI-assisted workflow evidence, an English report, PDF slides and a demonstration of at least two minutes [1,2]. Lecture 02 motivates a shared vocabulary, an observable system sequence and operation contracts [3].

---PAGE---
# 2. Domain analysis and behavior

[[DOMAIN]]

Figure 2. Domain concepts in one local workspace. A scenario obtains source IDs from its calculation. The database stores one current plan as settings.

| Concept | Meaning and key data |
| --- | --- |
| Transaction | One recorded event: ID, date, description, positive amount in fen, kind, category and fingerprint |
| Budget | One recurring monthly category limit. Alerts compare it with the latest imported month |
| SavingsScenario | Target, current savings, horizon and hypothetical category cuts, with calculated results |
| AuditEvent | Timestamp, action and before/after or result details for an import, edit, budget or plan |

### Observable system sequence
The user submits CSV text. The system returns either an inserted/duplicate summary or a rejection reason. The user requests the overview and receives totals plus record IDs. A user may request a category suggestion, inspect its source, then apply it with an edit request. Suggesting alone changes no saved transaction. The user submits scenario inputs and receives a saved calculation and assumptions. These are external requests and results. Parsing, SQL insertion and model response validation remain internal collaborations.

### Operation contracts and invariants
| Operation | Success | Rejection / preservation |
| --- | --- | --- |
| importCSV | Save each validated new record once and record the import audit event | Any invalid row saves no records. Persistence failure rolls back records and audit |
| editTransaction | Save validated values with the same ID and a human correction audit | Invalid values or conflicting fingerprint change no transaction |
| suggestCategory | Return a labeled proposal with saved=false | Missing model or invalid response returns an explicit rules fallback. No ledger write |
| calculatePlan | Save valid inputs and return exact derived values with sources | Invalid target, horizon or reductions leave saved inputs unchanged |

Money is a positive exact integer in fen. Expense categories cannot be Income or Transfer. A fingerprint is unique across date, normalized description, amount and kind. Transfers never contribute to income or expense totals. Unknown descriptions receive Other and need review. Each observable result must identify its assumptions and relevant source records.

---PAGE---
# 3. Architecture and design choices

[[ARCHITECTURE]]

Figure 3. Browser-to-database workflow and optional model boundary. The external model returns a proposal without storage access.

### Module responsibilities
The frontend renders state, charts, source tables, review controls and scenario forms. app.py serves a fixed list of static assets and translates HTTP requests into domain operations. ledger/service.py owns validation, transaction identity, calculations, audit persistence and the optional model adapter. SQLite stores transactions, budgets, settings and audit events. tests and scripts verify the boundary using isolated temporary databases. The application needs Python 3.10+ and a browser, with no third-party runtime packages.

### Decisions compared with alternatives
| Choice | Alternative | Reason and cost |
| --- | --- | --- |
| Standard-library Python HTTP + vanilla JS | Framework frontend/API stack | Small local setup and easy inspection. Less routing, validation and deployment support |
| SQLite transactions and unique fingerprint | Browser-only storage | Central persistence and rollback. Single-user scope and no schema migration system |
| Integer fen with Decimal conversion | Binary float amounts | Exact imported money and independent expected-value tests. Explicit rounding for averages |
| Reviewed category proposal | Automatic model writes | Invalid suggestions cannot directly change records. Extra review action for each proposal |
| Fixed grounded Q&A tools | Free-form model-generated explanations | Source IDs and stable arithmetic. Narrow language and query coverage |

The model dependency is isolated behind a callable provider seam, which allows tests to inject outputs and failures. This verifies the adapter contract without calling an external service or confusing a fake response with model intelligence. A single service module suits this prototype, but growing import formats or multi-user features would justify splitting persistence and use-case responsibilities.

---PAGE---
# 4. Implementation and calculations

### Validation, import and correction
CSV requires distinct date, description, amount and kind headers. category is optional. The parser accepts UTF-8 with an optional byte-order mark and quoted descriptions. It checks every row before persistence. Dates must be valid ISO calendar dates, descriptions contain 1-300 characters, amounts are finite positive CNY values with at most two decimal places, and category agrees with kind. A SHA-256 fingerprint prevents repeated records, including concurrent duplicate imports. A database transaction includes both writes and audit details. A human category edit retains the record identity and records the change.

### Exact overview and scenario formulas
The overview selects three calendar months ending at the latest imported month. It includes missing months as zero and excludes transfers from both income and spending. It does not infer an unrecorded salary or extrapolate a partial month. Let I and E be the selected income and expense totals, n the horizon, T the target, S existing savings, E_c category spending and r_c the cut fraction.

Baseline monthly capacity B = round_fen((I - E) / 3).

Monthly reduction C = sum_c round_fen((E_c / 3) x r_c).

Required monthly savings R = ceil_fen(max(T - S, 0) / n).

Projection P = S + n x (B + C). Gap G = max(T - P, 0).

The scenario is feasible when P is at least T. Negative baseline capacity represents spending exceeding income. The projection can decline under that condition. A valid target already covered by current savings requires zero additional monthly savings, although the future spending scenario can still reduce projected holdings.

| Synthetic sample quantity | Value (RMB) |
| --- | --- |
| Three-month income / spending | 12,000.00 / 10,200.00 |
| Mean monthly savings capacity | 600.00 |
| Shopping, Entertainment, Food monthly mean | 650.00, 320.00, 850.00 |
| Reductions at 30%, 50%, 10% | 195.00 + 160.00 + 85.00 = 440.00 |
| Six-month projection / target | 6,240.00 / 6,000.00 |
| Four-month projection / gap | 4,160.00 / 1,840.00 |

The goal inputs persist. Subsequent record changes recompute the scenario. Budget reminders use the latest imported month and expose their contributing IDs.

---PAGE---
# 5. Verification and measured results

### Reproducible evidence
Run python scripts/verify.py from the project root. It creates temporary databases, runs the domain/HTTP suite and writes verification.json, test_log.txt and sample_state.json under output/evidence. The browser replay script separately drives a real Edge browser. Tests use independently stated expected values, preservation checks and failure injection. The files retain the actual runtime version and run timestamp.

[[RESULTS]]

The normal path and the failure path exercise the same interface/backend/database boundary. The browser checks imported totals, duplicate counts, category provenance, correction, review, six- and four-month plans, a budget alert, a grounded answer, a refused request, atomic CSV rejection and the mobile layout. No uncaught page errors appeared in the delivered browser run. The app-wide mobile viewport had no horizontal overflow, while the transaction table intentionally scrolls within its container.

### Evidence that explains a failure
The invalid fixture places one valid row before an impossible date. The batch rejection test requires zero persisted rows, rather than merely checking the presence of an error message. The audit-failure injection test requires zero records after a simulated persistence failure. The concurrent import test requires exactly 30 saved records across two simultaneous identical imports. These checks target state invariants that a successful screenshot cannot establish.

The first evaluation script accidentally queried a temporary database after its directory closed. The agent corrected the lifetime boundary. The first browser replay treated an already-visible success message as evidence that a new request had finished. The agent changed the check to wait for the specific new projection. The verification record discloses these corrections as agent work.

No load testing, accessibility audit, real bank data study, multiuser security assessment or longitudinal savings outcome has been performed. Passing the current tests establishes the specified local cases only.

---PAGE---
# 6. AI role, evaluation and supervision

### Two roles with separate evidence
Development assistance: OpenAI Codex inspected the brief and drafted code, tests and delivery material. The initial package contains substantial AI-authored work. The human user selected the finance topic and authorized implementation. Team-level code review, actual changes and final acceptance have not been documented yet. docs/AI_USAGE.md records the agent tasks, fixes and pending human review.

Runtime assistance: the optional Chat Completions adapter sends a merchant description as untrusted data and requests JSON containing exactly category and confidence [6,7]. It neither sends amounts nor allows tool use. The service checks the exact keys, an allowed expense category, finite numeric confidence and the 0-1 range. The user must explicitly apply the proposal using the edit flow. A timeout or invalid response returns a rules fallback. A valid schema does not guarantee correct semantics. Confidence is self-reported and uncalibrated.

[[EVALUATION]]

### Dataset and interpretation
The 20 merchant descriptions are synthetic labels authored during development and informed by the rules vocabulary. They are a convenience sample rather than an independent or representative test set. Eighteen labels match. Lidl weekly basket defaults to Other instead of Food, and Spotify premium defaults to Other instead of Entertainment. These errors expose missing merchant vocabulary and support the need for human review. They do not establish superiority over a language model or another product.

The nine authored Q&A cases cover six supported questions and three refusals. Matching expected numbers and source IDs verifies these constrained tool paths. It does not measure arbitrary natural-language understanding. Injected fake providers verify invalid schema fallback and preservation of ledger state. No live API request or live model accuracy assessment was performed.

### Next evaluation
The team should create an independently labeled held-out set, fix the prompt and model identifier, then compare rules and a real provider on the same descriptions. Report category accuracy, review rate, invalid-response rate, cost, latency and disagreement cases. Use synthetic or properly consented records. A separate reviewer should verify labels. Keep actual outputs and failures before making live-model quality claims.

---PAGE---
# 7. Failure handling, boundaries and limitations

| Risk / abnormal input | Implemented handling | Remaining limit |
| --- | --- | --- |
| Impossible date, NaN or wrong kind | Validate complete file and reject batch | No generic bank-export dialect support |
| Repeated import or conflicting edit | Unique fingerprint, duplicate summary or edit rejection | Identical genuine purchases need distinguishing descriptions |
| Persistence failure | Database rollback and API retry message | No operational backup or recovery study |
| Invalid model output / timeout | Schema checks and explicit baseline fallback | Semantically wrong valid categories still require review |
| Unsupported Q&A or instruction injection | Constrained scope response, no tool or write access | Keyword intent recognition has limited language coverage |
| Missing or partial months | Explicit three-month assumption, zero missing months | Incomplete data can distort the scenario |
| Budget overrun | In-app alert with latest-month source IDs | No notifications or future cash-flow prediction |

### Local data and HTTP boundary
The server binds to 127.0.0.1. Requests must use its localhost/loopback Host header. Mutations require a random session token, JSON content and a same-origin request when an Origin header is supplied. The frontend escapes imported text before constructing the table. Static routes allow only known assets. Export prefixes spreadsheet formula syntax to reduce accidental execution when opened in a spreadsheet. API credentials remain in server environment variables. This is a local teaching boundary, not multiuser authentication or a production security certification.

### Limitations with practical consequences
The single-user ledger supports CNY and positive amounts only. Refunds require a future signed-amount or explicit refund model. The UI edits categories and the API supports broader record edits. A zero model confidence is a request for review, not evidence of correctness. Audit history is inspectable but not tamper-proof. The sample records are synthetic and the application has not demonstrated improved financial outcomes. The Python HTTP server and database design need production hardening before shared deployment.

All budget and scenario claims depend on the imported records being complete and on the user understanding that reductions are assumptions. A saved target is a scenario input, not an automatic transfer of funds. The system performs no banking, trading or external message action.

---PAGE---
# 8. Reproduction, team record and references

### Reproduction and delivered artifacts
Run python app.py and open http://127.0.0.1:8765. Load the sample records. Use the six-month scenario and the invalid fixture as described in README. The application uses only the Python standard library. Optional live model use needs independently supplied provider credentials and a JSON-mode-compatible model. The captioned recording demonstrates real browser interaction for more than two minutes. PDF slides, an editable presentation, a retrospective one-slide proposal draft, source files, test logs and evaluation JSON accompany this report.

### Team accountability
Names, IDs and actual member contributions have not been supplied. docs/CONTRIBUTIONS.md provides a record for actual requirements, implementation, review and evaluation contributions. No human implementation contribution has been invented. The team should inspect the initial AI-assisted implementation, make and document its own changes, rerun verification and rehearse explaining the full system. The provided course materials require disclosure of outside/AI help and shared responsibility [2]. The initial report remains subject to that team review and attribution.

### References
[1] Xiaowei Hu. Project Kick-off. Comprehensive Design of Computer Science and Software Engineering, 23 September 2026. Supplied Project_Kickoff.pdf, especially project requirements and Project 2.

[2] Xiaowei Hu. Lecture 01: Software Engineering in the AI Era. September 2026. Supplied 01_AI_Era_Software_Engineering.pdf, especially teamwork, AI responsibility and final deliverables.

[3] Xiaowei Hu. Lecture 02: Requirements and Object-Oriented Analysis. Supplied CSSE2026/02_Requirements_and_Object_Oriented_Analysis.pdf. Domain concepts, sequence diagrams and operation contracts.

[4] Actual Budget contributors. Actual repository and README. https://github.com/actualbudget/actual . Accessed 9 October 2026. Related-work comparison only.

[5] Firefly III contributors. Firefly III repository and README. https://github.com/firefly-iii/firefly-iii . Accessed 9 October 2026. Related-work comparison only.

[6] OpenAI. Create chat completion API reference. https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create . Accessed 9 October 2026. Optional integration contract.

[7] OpenAI. Structured model outputs and JSON mode. https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses . Accessed 9 October 2026. JSON parsing still requires application schema validation.

[8] Python Software Foundation. sqlite3 documentation. https://docs.python.org/3.13/library/sqlite3.html . Accessed 9 October 2026. SQLite transactions and Python DB-API.
