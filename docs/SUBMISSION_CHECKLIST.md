# Submission checklist

The supplied Project Kickoff specifies a runnable system, code repository and README, final slides as PDF, a system demonstration of at least two minutes, and an English technical report. Lecture 01 additionally names proposal slides, test evidence, AI evaluation and disclosed external/AI assistance. No precise final submission deadline appears in the supplied files.

| Requirement | Local artifact / evidence | Status |
| --- | --- | --- |
| Usable interface, backend, connected data | `static/`, `app.py`, `ledger/service.py`, SQLite | Implemented and verified locally |
| Main workflow | Import, inspect, correct, plan, query, monitor | Browser-tested |
| Failure handling | `samples/invalid.csv`, rollback and provider-failure tests | Verified |
| Source repository and README | Current local Git workspace and `README.md` | Present locally. Remote repository URL not supplied |
| Final PDF slides | `output/LedgerLens_Final_Slides.pdf` | Included |
| English technical report | `output/pdf/LedgerLens_Technical_Report.pdf` | Included |
| At least two-minute demo | `output/LedgerLens_Demo.webm` | Recorded with English captions |
| Proposal slides and PDF | Same-name PDF / PPTX in `output/精美版/`, named with all three student IDs and names | Ten-slide polished English presentation; Chen Tianyu leads core development; speaker notes retained; PDF has slide bookmarks and contents links |
| English proposal script | `docs/PROPOSAL_SPEAKING_NOTES_EN.md` and PPT speaker notes | 575 spoken words with simple vocabulary; approximately five minutes; timing guide included; concrete examples appear in English Q&A |
| Printable English proposal script | `output/pdf/PROPOSAL_SPEAKING_NOTES_EN.pdf` | Five A4 pages; practice guide, unchanged main script and separate English Q&A; text and layout checked |
| AI workflow implementation | `docs/CODE_UPDATE_2026-10-15.md`, `docs/AI_WORKFLOW_EXTENSION_PLAN.md` | 分类记忆, tool calling, conversations, constrained plans and monthly reviews implemented; independent evaluation pending |
| Goal adventure | `ledger/adventure.py`, `static/adventure.*`, `docs/GAMEPLAY_DESIGN.md` | Implemented, 24 new tests and complete browser journey; motivation outcomes unmeasured |
| Engineering evidence | `output/evidence/` | Recorded tests and baseline evaluation |
| AI usage statement | `docs/AI_USAGE.md` and report | Included. Student review details pending |
| Member contributions | `docs/CONTRIBUTIONS.md` | Names and IDs supplied. Proposed roles recorded. Actual contributions still required |
| English defense | `docs/DEFENSE_NOTES.md` | Script and Q&A included. Student rehearsal required |

For the opening presentation, use **`output/精美版/202464870547-陈天宇-202464871352-朱俊丞-202464871290-张瀚文.pdf`** or its same-name editable PPTX. The PPT notes preserve the simple script and the final slide's corrected team roles. The retained proposal files describe the original planned stage and baseline evidence. The code now implements memory, model-driven queries, checked plans and monthly reviews. Current evidence is 107 tests, three browser replays and six small synthetic DeepSeek integration checks. Independent model quality and research remain pending; team roles are proposed. Update the final report/slides/video after accepting the new code. The earlier ten-slide deck, dated one-page presentation and Chinese script (`docs/PROPOSAL_SPEAKING_NOTES.md`) remain available for reference. The twelve-slide final presentation is for the final defense.

Before final submission: add the actual course/team repository URL if required, check the instructor's announced deadline and report format, review and understand the code, rerun checks, and record actual human contributions, changes and acceptance. Real API integration has been smoke-tested. An independent held-out evaluation is still needed before claiming model performance. The private provider key and user databases are excluded from the submission ZIP.
