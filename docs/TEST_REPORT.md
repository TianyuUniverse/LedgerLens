# Test and evaluation report

> 当前账单页更新：175 项自动测试及六组浏览器检查通过。新增内容来源记录与简洁账单视图，旧记录不猜测是否由 AI 整理。见 [账单来源说明](RECORDS_UI.md)。


> 2026-10-20 当前更新：微信原生 XLSX 预览与确认导入、分类记忆流程修复、游戏界面撤下并保留储蓄目标。当前 168 项自动测试及五组浏览器流程通过；两次合成数据真实模型记忆检查通过。详见 [当前说明](WECHAT_IMPORT_AND_MEMORY.md)。下面按日期保留历史证据，不代表旧游戏仍在界面中。


Updated 20 October 2026. Run `python scripts/verify.py` to reproduce the 150 domain/HTTP tests and legacy baseline checks. Tests use temporary databases, no external provider calls, and do not change a personal ledger. The latest counts and timestamps are in `output/evidence/verification.json`; individual results are in `test_log.txt`. The original 28-test record is preserved under `output/evidence/baseline-20261009/`.

The suite covers exact fen arithmetic, complete-batch validation, duplicate/concurrent imports, audit-failure rollback, edits, calendar windows, manual scenarios, budgets and grounded answer sources. New memory checks cover original labels, correction from transfer to expense, future approved reuse, same-school tuition and unrelated-roommate counterexamples, generic payment-label rejection, true own-account transfers, conflicting/review-only memories, stale confirmation, versioning, disabling/deletion without rewriting history, migration/reopen and deduplication after kind correction.

New finance/conversation checks cover independent period totals and exclusions, source IDs, argument allowlists, fixed categories/floors, impossible targets, stale plan previews, monthly review evidence, persistent multi-turn context, ambiguous record/year handling, user constraint retention, bounded fake-model loops, discarded unsupported numeric claims, timeout/invalid-tool fallback, speculative-state rollback and explicit model opt-in. HTTP checks cover new routes, token/origin restrictions and private configuration path rejection.

Both browser replays use real Microsoft Edge through Playwright. `browser_check.json` records the original dashboard/import/edit/plan/budget/Q&A/failure flow. `workflow_browser_check.json` records confirmation, future reuse, financial-kind correction, tuition counterexample, memory editing/versioning/disable/enable/delete, generated plan preview/save/staleness, monthly review, Chinese follow-ups, preserved constraints and conversation reset. Both check uncaught JavaScript errors and strict 390px mobile overflow. Screenshots include `purpose-memory.png`, `checked-savings-plans.png`, `finance-conversation.png` and `workflows-mobile.png`.

The legacy rules benchmark remains 18/20: Lidl weekly basket and Spotify premium remain misses. The cases were authored with implementation knowledge and are not a held-out benchmark. Legacy grounded Q&A remains 9/9 authored cases; this measures scoped deterministic queries.

`live_model_smoke.json` records an explicit DeepSeek call on temporary synthetic data. Three conversational requests passed: month comparison, a goal with fixed rent and entertainment minimum, and a follow-up fixing Food. Three context-based proposals passed: school meals as Food, roommate utilities as expense/Utilities, and an own-account transfer retained as Transfer. The ledger did not change. These six development checks establish integration on those inputs, not real-world accuracy, calibrated confidence or representative task completion. No user-study outcome is claimed.

The existing 138.64-second captioned video demonstrates the earlier rules baseline. It has not been re-recorded for the new workflows. Production load, independent model comparison, accessibility audit and real-user research remain outside the recorded evidence.

Chinese localization checks additionally cover Chinese CSV headers/kinds/categories, alias collisions, exported-record identity, spreadsheet formula escaping, preserved user text, Chinese answers for every financial result type, and translated HTTP validation. Browser replays assert Chinese system text and native form validation while retaining the existing financial checks.

The 19 October goal-adventure addition contributes 24 domain/HTTP tests: allocation arithmetic and unchanged financial records; goal capacity and archive/restore; input rejection; request replay/conflicts; concurrent retries; insufficient withdrawals; milestone deduplication after withdrawals; starting-progress handling; daily cross-goal XP cap; rollback of allocation/reward/audit together; new-row-only import rewards; real pending-purpose and memory rewards; reflection data requirements; Shanghai midnight, streak and weekly boundaries; theme authorization; persistence; read-only tool isolation; and protected HTTP routes.

`adventure_browser_check.json` records a complete synthetic journey: a RMB 1,000 goal, real import/review/memory/reflection/planning actions, milestone progress, withdrawal/redeposit, request replay, themes, archive/restore, persisted reload and 390px layout. The recorded path reaches RMB 1,000 and 375 XP at level 4 without external model calls. Scenery screenshots are `adventure-start.png`, `adventure-quarter.png`, `adventure-complete.png` and `adventure-mobile.png`. No engagement or real saving improvement has been measured.


## 2026-10-19 图鉴、AI 向导与简约界面

新增快速记账、周／月报告、折线图／环形图／目标轨迹／预算进度／六维雷达图、AI 建议与任务卡、四格分镜对白、预制卡通素材和游戏小狐向导。新增 22 项测试，当前自动测试合计 **129 项通过**。`scripts/reports_browser_check.cjs` 验证周期切换、来源、草稿与保存、六维图、素材、图表导出与 390px 布局；原三组浏览器流程继续验证。

`output/evidence/live_reports_check.json` 记录本轮 **2 次报告 + 1 次记账草稿** 的真实 DeepSeek 集成调用，全部成功，账本和经验未改动。只是三项合成场景，不能作为模型准确率或真实用户研究结果。周报和月报由应用打开／周期切换时本地计算；云端 AI 生成需主动勾选与点击，不声称软件关闭时也能定时生成。

公开仓库排除私人数据库、API 配置和历史输出材料；贡献分工仍为拟定分工。新增 CI、PR 模板、issue 模板与 CONTRIBUTING，不虚构多人开发历史。设计说明见 `docs/AI_REPORTS_DESIGN.md`。


## 2026-10-20 更新

当前版为七个独立视图，七类业务录入默认使用 AI 对话、可修改草稿与最后确认；训练场支持三关练习、角色移动和服务端每日奖励。按钮、滑条、输入框宽度和字号已统一，数字步进箭头与课程页脚已移除。原有手动表单保留为备用入口。完整说明、数据边界和复现命令见 [本轮更新](UPDATE_2026-10-20.md)。当前自动测试 150 项，浏览器检查五组；真实模型检查只使用合成数据，不能视为准确率或用户研究。
