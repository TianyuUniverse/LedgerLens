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


## 2026-10-19 图鉴、AI 向导与简约界面

新增快速记账、周／月报告、折线图／环形图／目标轨迹／预算进度／六维雷达图、AI 建议与任务卡、四格分镜对白、预制卡通素材和游戏小狐向导。新增 22 项测试，当前自动测试合计 **129 项通过**。`scripts/reports_browser_check.cjs` 验证周期切换、来源、草稿与保存、六维图、素材、图表导出与 390px 布局；原三组浏览器流程继续验证。

`output/evidence/live_reports_check.json` 记录本轮 **2 次报告 + 1 次记账草稿** 的真实 DeepSeek 集成调用，全部成功，账本和经验未改动。只是三项合成场景，不能作为模型准确率或真实用户研究结果。周报和月报由应用打开／周期切换时本地计算；云端 AI 生成需主动勾选与点击，不声称软件关闭时也能定时生成。

公开仓库排除私人数据库、API 配置和历史输出材料；贡献分工仍为拟定分工。新增 CI、PR 模板、issue 模板与 CONTRIBUTING，不虚构多人开发历史。设计说明见 `docs/AI_REPORTS_DESIGN.md`。


## 2026-10-20 更新

当前版为七个独立视图，七类业务录入默认使用 AI 对话、可修改草稿与最后确认；训练场支持三关练习、角色移动和服务端每日奖励。按钮、滑条、输入框宽度和字号已统一，数字步进箭头与课程页脚已移除。原有手动表单保留为备用入口。完整说明、数据边界和复现命令见 [本轮更新](UPDATE_2026-10-20.md)。当前自动测试 150 项，浏览器检查五组；真实模型检查只使用合成数据，不能视为准确率或用户研究。
