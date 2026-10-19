# Requirements, domain and system sequence

## Traceability matrix

| ID | Requirement | Main implementation | Evidence |
| --- | --- | --- | --- |
| R1 | Validate complete CSV and reject invalid batches without partial state | Ledger.import_csv | test_atomic_rejection, test_rollback_on_audit_failure |
| R2 | Prevent repeated record identity and concurrent duplicate counting | unique transaction fingerprint | test_import_counts_and_repeat_duplicates, test_concurrent_duplicate_import |
| R3 | Show exact income/spending with transfers excluded | Ledger.overview | test_overview_exact_and_transfer_excluded |
| R4 | Allow category corrections and preserve audit | Ledger.edit, category dropdown | test_edit_category_recalculates_and_audits, browser replay |
| R5 | Compare goal, horizon and budget reductions | Ledger.plan | test_plan_expected_independent_arithmetic, test_change_horizon_creates_gap |
| R6 | Link analysis and answers to source records | record_ids in overview, plan and answers | test_answer_sources_sum_to_claim, browser category trace |
| R7 | Monitor recurring user budgets | Ledger.set_budget, state budget alerts | test_budget_overrun_source_ids |
| R8 | Keep AI proposals under human control | Ledger.suggest, review dialog and explicit PATCH | test_model_proposal_never_writes, browser cancel/review |
| R9 | Recover from invalid model output and timeout | injected provider seam and rules fallback | test_model_bad_output_fallback, test_model_timeout_fallback |
| R10 | Handle unsupported questions clearly | constrained deterministic answer tools | test_unsupported_and_injection_rejected |

## Domain model

```mermaid
classDiagram
class Workspace {
  local SQLite file
}
class Transaction {
  id
  date
  description
  amount_fen
  kind
  category
  fingerprint
}
class Budget {
  category
  limit_fen
}
class SavingsScenario {
  target
  current
  months
  cuts
}
class AuditEvent {
  at
  action
  details
}
Workspace "1" --> "0..*" Transaction
Workspace "1" --> "0..*" Budget
Workspace "1" --> "0..1" SavingsScenario : saved current plan
Workspace "1" --> "0..*" AuditEvent
```

The Workspace denotes the local data boundary, not a separate user/authentication table. Source associations for calculations are computed record IDs rather than persisted scenario-to-transaction join rows.

## System sequence: import and analyze

```mermaid
sequenceDiagram
participant User
participant System as LedgerLens system
User->>System: importCSV(text)
alt Every row is valid
System-->>User: inserted count, duplicate count, IDs
User->>System: requestOverview()
System-->>User: totals, categories, source IDs, assumptions
else Any row is invalid
System-->>User: rejection(reason), no saved rows
end
```

## System sequence: supervised category suggestion

```mermaid
sequenceDiagram
participant User
participant System as LedgerLens system
User->>System: suggestCategory(recordID)
System-->>User: proposal(category, confidence, source, saved=false)
alt User applies proposal
User->>System: editTransaction(recordID, category)
System-->>User: saved correction, updated overview, audit entry
else User cancels
Note over User,System: Ledger state remains unchanged
end
```

## Decision log

ADR-001: Use a Python standard-library HTTP server and vanilla JavaScript for local setup simplicity. A framework would help a larger deployed system. Current scope is loopback and single user.

ADR-002: Use integer fen and Decimal parsing instead of floats. Round each average/category reduction explicitly. Exact-money tests use expected values derived independently from the sample fixture.

ADR-003: Put all batch writes and audit in a SQLite transaction and use a unique fingerprint. Browser-only storage would weaken rollback/persistence demonstration. Identical genuine purchases need a distinguishing description.

ADR-004: Treat model output as an untrusted category proposal. Keep money outside the model and preserve human confirmation. A valid schema is a necessary check but cannot establish category correctness.

ADR-005: Use tool-based deterministic answers for a narrow query set. Free-form generation would increase unsupported numerical claims and evaluation burden. Language coverage is intentionally limited and disclosed.
