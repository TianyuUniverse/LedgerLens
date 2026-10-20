# Submission checklist

> 当前账单页更新：186 项自动测试及六组浏览器检查通过。新增内容来源记录、简洁账单视图及单笔删除确认，旧记录不猜测是否由 AI 整理。见 [账单来源说明](RECORDS_UI.md)。


> 2026-10-20 当前更新：微信原生 XLSX 预览与确认导入、分类记忆流程修复、游戏界面撤下并保留储蓄目标。当前 168 项自动测试及五组浏览器流程通过；两次合成数据真实模型记忆检查通过。详见 [当前说明](WECHAT_IMPORT_AND_MEMORY.md)。下面按日期保留历史证据，不代表旧游戏仍在界面中。


The supplied Project Kickoff specifies a runnable system, code repository and README, final slides as PDF, a system demonstration of at least two minutes, and an English technical report. Lecture 01 additionally names proposal slides, test evidence, AI evaluation and disclosed external/AI assistance. No precise final submission deadline appears in the supplied files.

| Requirement | Local artifact / evidence | Status |
| --- | --- | --- |
| Usable interface, backend, connected data | `static/`, `app.py`, `ledger/service.py`, SQLite | Implemented and verified locally |
| Main workflow | Import, inspect, correct, plan, query, monitor | Browser-tested |
| Failure handling | `samples/invalid.csv`, rollback and provider-failure tests | Verified |
| Source repository and README | Current local Git workspace and `README.md` | Public repository: https://github.com/TianyuUniverse/LedgerLens |
| Final PDF slides | `output/LedgerLens_Final_Slides.pdf` | Included |
| English technical report | `output/pdf/LedgerLens_Technical_Report.pdf` | Included |
| At least two-minute demo | `output/LedgerLens_Demo.webm` | Recorded with English captions |
| Proposal slides and PDF | Same-name PDF / PPTX in `output/精美版/`, named with all three student IDs and names | Ten-slide polished English presentation; Chen Tianyu leads core development; speaker notes retained; PDF has slide bookmarks and contents links |
| English proposal script | `docs/PROPOSAL_SPEAKING_NOTES_EN.md` and PPT speaker notes | 575 spoken words with simple vocabulary; approximately five minutes; timing guide included; concrete examples appear in English Q&A |
| Printable English proposal script | `output/pdf/PROPOSAL_SPEAKING_NOTES_EN.pdf` | Five A4 pages; practice guide, unchanged main script and separate English Q&A; text and layout checked |
| AI workflow implementation | `docs/CODE_UPDATE_2026-10-15.md`, `docs/AI_WORKFLOW_EXTENSION_PLAN.md` | 分类记忆, tool calling, conversations, constrained plans and monthly reviews implemented; independent evaluation pending |
| Ordinary savings goals (game UI retired) | `ledger/adventure.py`, `static/adventure.*`, `docs/GAMEPLAY_DESIGN.md` | Savings records retained; game UI removed at user request; current browser tests cover savings and legacy URLs |
| Engineering evidence | `output/evidence/` | Recorded tests and baseline evaluation |
| AI usage statement | `docs/AI_USAGE.md` and report | Included. Student review details pending |
| Member contributions | `docs/CONTRIBUTIONS.md` | Names and IDs supplied. Proposed roles recorded. Actual contributions still required |
| English defense | `docs/DEFENSE_NOTES.md` | Script and Q&A included. Student rehearsal required |

For the opening presentation, use **`output/精美版/202464870547-陈天宇-202464871352-朱俊丞-202464871290-张瀚文.pdf`** or its same-name editable PPTX. The PPT notes preserve the simple script and the final slide's corrected team roles. The retained proposal files describe the original planned stage and baseline evidence. The code now implements memory, model-driven queries, checked plans and monthly reviews. Current evidence is 129 tests, three browser replays and six small synthetic DeepSeek integration checks. Independent model quality and research remain pending; team roles are proposed. Update the final report/slides/video after accepting the new code. The earlier ten-slide deck, dated one-page presentation and Chinese script (`docs/PROPOSAL_SPEAKING_NOTES.md`) remain available for reference. The twelve-slide final presentation is for the final defense.

Before final submission: add the actual course/team repository URL if required, check the instructor's announced deadline and report format, review and understand the code, rerun checks, and record actual human contributions, changes and acceptance. Real API integration has been smoke-tested. An independent held-out evaluation is still needed before claiming model performance. The private provider key and user databases are excluded from the submission ZIP.


## 2026-10-19 图鉴、AI 向导与简约界面

新增快速记账、周／月报告、折线图／环形图／目标轨迹／预算进度／六维雷达图、AI 建议与任务卡、四格分镜对白、预制卡通素材和游戏小狐向导。新增 22 项测试，当前自动测试合计 **129 项通过**。`scripts/reports_browser_check.cjs` 验证周期切换、来源、草稿与保存、六维图、素材、图表导出与 390px 布局；原三组浏览器流程继续验证。

`output/evidence/live_reports_check.json` 记录本轮 **2 次报告 + 1 次记账草稿** 的真实 DeepSeek 集成调用，全部成功，账本和经验未改动。只是三项合成场景，不能作为模型准确率或真实用户研究结果。周报和月报由应用打开／周期切换时本地计算；云端 AI 生成需主动勾选与点击，不声称软件关闭时也能定时生成。

公开仓库排除私人数据库、API 配置和历史输出材料；贡献分工仍为拟定分工。新增 CI、PR 模板、issue 模板与 CONTRIBUTING，不虚构多人开发历史。设计说明见 `docs/AI_REPORTS_DESIGN.md`。


## 2026-10-20 更新

当前版为七个独立视图，七类业务录入默认使用 AI 对话、可修改草稿与最后确认；训练场支持三关练习、角色移动和服务端每日奖励。按钮、滑条、输入框宽度和字号已统一，数字步进箭头与课程页脚已移除。原有手动表单保留为备用入口。完整说明、数据边界和复现命令见 [本轮更新](UPDATE_2026-10-20.md)。当前自动测试 150 项，浏览器检查五组；真实模型检查只使用合成数据，不能视为准确率或用户研究。
