# Defense notes

## English opening (about 40 seconds)

Our project is LedgerLens, a personal finance assistant for students who import transaction records and want to understand their spending and compare a savings goal. We implemented one complete workflow: import a CSV, inspect a traceable overview, correct a category, calculate a scenario and monitor a budget. The interface, Python backend and SQLite database run locally. All monetary results come from integer-fen calculations. The delivered demonstration uses a labeled rules baseline. A language model can optionally propose categories, but a person must review a proposal before it changes a record.

## English two-minute live demo script

0:00-0:20: Load sample data. Explain that 30 records are synthetic and the three-month spending total is RMB 10,200.

0:20-0:35: Load the same file again. Show 30 skipped duplicates and the unchanged ledger.

0:35-0:55: Click Shopping. Show source IDs. Correct one category and explain the audit trail. Restore the category for the comparison.

0:55-1:15: Show the six-month RMB 6,000 goal and RMB 6,240 scenario. Explain RMB 600 baseline plus RMB 440 monthly reductions.

1:15-1:30: Change to four months. Show RMB 4,160 projection and RMB 1,840 gap.

1:30-1:45: Set Shopping budget to RMB 500. Show the September RMB 250 overrun.

1:45-2:00: Ask about spending and inspect sources. Import the invalid CSV and show atomic rejection. Allow extra time for explanation and questions.

## Questions and concise answers

**Where is the AI?** Codex assisted development and the disclosure records this. Runtime classification can use a real JSON-mode model provider. The delivered baseline uses keyword rules. Grounded Q&A uses deterministic tools. We do not claim the rules baseline is a language model.

**What did the team personally do?** This must be answered from the completed contribution and review records. The current initial package has substantial Codex assistance and no verified student implementation contribution yet.

**How did you get RMB 6,240?** Total income is 12,000 and expenses are 10,200 over three months. Baseline monthly capacity is (12,000 - 10,200) / 3 = 600. Mean monthly Shopping is 650, Entertainment is 320 and Food is 850. Reductions are 650 x 30% + 320 x 50% + 850 x 10% = 440. Six months at 1,040 gives 6,240, assuming stable future records and behavior.

**Why integer fen?** Each imported amount has at most two decimal places. Conversion with Decimal stores an exact integer. Aggregation does not accumulate binary floating-point rounding error.

**What if a file contains one invalid row?** Validate the complete batch first. Reject all rows. A database transaction also rolls back if persistence or audit writing fails.

**What prevents a model changing money?** The model sees only a description, returns a constrained category proposal and has no database/tool access. Schema validation rejects extra fields or invalid categories. Applying a proposal uses the ordinary edit endpoint under user control.

**What do your evaluation numbers mean?** Twenty rules-informed synthetic category examples yield 18 correct predictions. Nine authored Q&A cases pass. These small, development-authored sets are not independent evidence of real-world or live-model quality. The two category errors demonstrate missing merchant vocabulary.

**How do you prevent duplicates?** A unique fingerprint uses date, normalized description, amount and kind. Repeated imports do not double-count. Distinct purchases with otherwise identical fields need a distinguishing description.

**Why use this stack?** A standard-library Python server, SQLite and vanilla JavaScript reduce setup cost for a small local demonstration. Production use would require a production server, authentication, migrations, richer import formats and a wider evaluation.

**Why not use Actual Budget or Firefly III?** Both informed related-work comparison. This narrow prototype directly demonstrates our specified provenance, scenario and supervised classification workflow with a small inspectable codebase. We incorporated no code from either project.

## 中文复习提示

答辩前至少读懂三个点：钱如何从 CSV 变成整数「分」；一个错误如何保证不留下半批数据；为什么模型建议必须确认才保存。自己运行一次 6 个月和 4 个月情景，并解释为什么预算提醒检查的是最新导入月份。

不要说真实模型准确率为 90%：18/20 是规则分类的合成小样本结果。不要把 9/9 理解为所有自然语言问题都能回答。不要把 AI 编写的实现描述成某个成员独立完成。
