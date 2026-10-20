# 团队协作约定

这个仓库把已有的 AI 辅助原型作为首次提交。提交历史不代表三位同学已经分别完成各模块。拟定分工与后续实际贡献证据见 [贡献记录](docs/CONTRIBUTIONS.md)。

1. 将工作写成一个可演示、可验证的 issue，明确输入、输出和验收条件。
2. 从 `main` 创建功能分支。Codex 辅助分支使用 `codex/` 前缀。
3. 完成实际实现与必要验证后提交，提交信息描述具体变化。
4. 发起 PR，说明用户行为、验证结果和需要关注的限制。由另一位实际成员检查并填写真实审核意见。
5. 检查 CI，再决定是否合并。贡献表链接到实际提交、PR 或测试证据。

不要修改 Git 作者来模拟其他同学提交；不要把尚未开展的访谈或用户测试写成已完成研究。

本地验证：

```powershell
python -X utf8 -m unittest discover -v
python scripts/check_shared_files.py
```

CI 在 Windows 与 Linux、Python 3.11 与 3.13 上验证领域与 HTTP 测试，并检查前端 JavaScript 语法。浏览器演示检查需自行安装 Playwright 和 Edge，记录在 PR 中；CI 不调用收费模型。

私人配置放在 `data/provider.json`，参考 `samples/provider.example.json`；禁止提交真实账单、数据库、密钥或截图中的个人财务数据。
