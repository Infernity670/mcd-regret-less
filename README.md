# 麦麦后悔药 · mcd-regret-less

**保留最想吃的东西，算清省钱需要什么取舍。**

基于麦当劳中国 MCP 的点餐比较 Skill，为有预算、又不愿随意更换喜欢餐品的用户设计。WorkBuddy 理解偏好，真实工具查询套餐和优惠，Python 比较有效报价，输出「按你的心意」「小改一下」「预算优先」。

> 当前状态：已完成本地比较器验证，并已记录首轮WorkBuddy真实MCP验收。外送、非空优惠券和下单路径尚未验证。演示夹价格全部虚构，真实验收摘要见MCP_INTEGRATION.md。本项目为独立参赛作品，非麦当劳官方产品。

## 使用示例

「我想吃汉堡、中薯和可乐，预算30元，汉堡一定要保留。」

以下仅为**虚构演示价格**，不代表真实菜单、售价、套餐或优惠：

| 方案 | 到手内容 | 演示价 | 相比原单36元 | 取舍 |
|---|---|---:|---:|---|
| 按你的心意 | 汉堡＋中薯＋可乐 | 32元 | 省4元 | 保留全部，超预算2元 |
| 小改一下 | 汉堡＋小薯＋可乐 | 29元 | 省7元 | 中薯换小薯 |
| 预算优先 | 汉堡 | 24元 | 省12元 | 不含薯条和可乐 |

继续说「可乐不要动」，预算优先方案就必须保留可乐。「预算改35」保留其他偏好，只重新比较预算；换门店、规格或券则重新试算。

## 本地快速运行

Python 3.11+，无第三方依赖。解压后进入项目根目录：

```powershell
python -m unittest discover -s tests -v
python skills/mcd-regret-less/scripts/planner.py compare examples/demo-candidates.json --now 2026-10-10T12:00:00+08:00
python skills/mcd-regret-less/scripts/planner.py update examples/demo-preferences.json examples/lock-cola.patch.json
```

`--now` 仅为固定时间的离线演示服务；live 模式使用系统当前时间，不能回拨时间使用过期报价。update 输出完整新偏好，compare 输入的 preferences 换成该输出即可继续比较。

## 在 WorkBuddy 安装

下载 [WorkBuddy技能包](dist/mcd-regret-less-skill.zip)。打开WorkBuddy的「专家·技能·连接器」→「技能」→「添加技能」→「上传技能」，选择mcd-regret-less-skill.zip。导入后在已安装列表中启用。

也可以在WorkBuddy中打开完整项目文件夹，并让它读取 `skills/mcd-regret-less/SKILL.md` 及引用文件执行流程。Python比较器只处理JSON，不独立理解自然语言或查询菜单。

[WorkBuddy官方技能安装说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。技能包采用 [WorkBuddy官方技能结构](https://open.workbuddy.cn/docs/skill)，提供名称、双语描述、版本与作者字段。

## 连接真实 MCP

在 https://open.mcd.cn/mcp 自行申请 Token。服务器 `https://mcp.mcd.cn`，传输为 Streamable HTTP，鉴权来自本地环境变量 `MCD_MCP_TOKEN`。参见 [脱敏配置](mcp-config.example.json) 和 [真实联调手册](skills/mcd-regret-less/references/live-workflow.md)。

配置示例中的 `${MCD_MCP_TOKEN}` 是环境变量占位符。请按WorkBuddy当前配置说明使用本地环境变量或凭证设置，不把包含真实 Token 的配置提交仓库。

WorkBuddy连接读取实际 schema，并响应用户当前具体请求调用工具。官方公开 README 未列完整参数，需要依据WorkBuddy实际工具说明和上游结果使用参数，不凭空构造官方字段。服务规则禁止脚本/爬虫/自动化调用，因此项目不附带直连官方服务的网络脚本，也不实现批量搜索、自动轮询或后台调用。

## 特点与边界

- 不可替换餐品是硬约束；预算不足时说明最小缺口。
- 以最终应付价比较，明确少了什么、多了什么、改了什么。
- 所有金额使用整数分，试算失败、过期和上下文不同的报价排除。
- 只说已核验候选中的最低价，不承诺全菜单最优。
- 用户确认后才由WorkBuddy创建订单；Python不提供网络调用、下单或支付。
- 原始参数和响应进入被 Git 忽略的 private/，不能原样公开。

第一版单人使用；不提供多人账号拼券、营养处方、自动支付、会员卡购买或跨品牌比较。若出现缺项、无券、工具失败，不虚构补足。

## 项目内容

| 路径 | 用途 |
|---|---|
| skills/mcd-regret-less/SKILL.md | WorkBuddy 的实际工作流程 |
| skills/mcd-regret-less/scripts/planner.py | 确定性比较与增量偏好更新 |
| skills/mcd-regret-less/references/ | 内部契约和真实接入指南 |
| examples/ | 虚构输入、偏好更新、实际生成的演示输出 |
| tests/ | 比较器行为测试，不代表真实 MCP 联调 |
| PLAN.md | 制作计划、赛事要求和验收范围 |
| MCP_INTEGRATION.md | 工具、调用流程、业务价值与联调状态 |
| docs/ | 参赛检查、发布步骤和演示脚本 |

核心代码与 Skill 原创编写，代码/原创文档采用 MIT；官方参赛声明原样保留，第三方条款和官方内容不因本仓库许可证获得额外授权。详见 LICENSE 与 docs/ATTRIBUTION.md。
