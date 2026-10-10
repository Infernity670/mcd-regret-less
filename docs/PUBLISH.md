# 发布与报名

公开仓库：https://github.com/Infernity670/mcd-regret-less

## 从WorkBuddy发布源码

在WorkBuddy打开解压后的完整项目文件夹，在项目根目录的终端按顺序运行以下命令。首次提交前设置项目本地的Git作者信息；邮箱使用自己在GitHub设置的提交邮箱。登录验证在本机完成，不把Token写进命令或文件。

```powershell
git init
git config user.name Infernity670
git config user.email "你的GitHub提交邮箱"
git add README.md CONTEST_DECLARATION.md MCP_INTEGRATION.md mcp-config.example.json PLAN.md LICENSE .gitignore skills examples tests docs dist/mcd-regret-less-skill.zip
git diff --cached --stat
git commit -m "Add meal preference skill and MCP integration"
git branch -M main
git remote add origin https://github.com/Infernity670/mcd-regret-less.git
git push -u origin main
```

若项目已经初始化或已有origin，先检查git status与git remote -v，不重复执行初始化/添加远程步骤。推送后在公开仓库核对README、声明、集成说明、配置示例及安装包都可读取。

## 参赛材料

根目录须包含README.md、CONTEST_DECLARATION.md、MCP_INTEGRATION.md、mcp-config.example.json与可运行内容。官方声明原样保留，原始请求和响应只保存在private/。不要公开.env、凭证、日志、缓存、账号数据、完整地址或订单信息。

首轮真实验收摘要已记录在MCP_INTEGRATION.md。发布前核对实际能力和未验证范围；WorkBuddy真实对话上下文导出并脱敏后，才将workbuddy.md加入仓库。若没有该文件，不宣称满足WorkBuddy专项条件。

完成参赛声明与资格确认后，按REGISTRATION_DRAFT.md在官方比赛仓库提交报名Issue，查看系统成功通知。报名截止2026-10-25 23:59（北京时间）。公开分享可运行项目，禁止批量账号、刷榜或操纵Star。
