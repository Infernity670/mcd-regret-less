# WorkBuddy MCP 接入与真实联调

本 Skill 通过官方文档支持的WorkBuddy客户端响应用户具体请求，Python只处理已获取的数据。服务规则禁止脚本/爬虫/自动化工具调用，因此不要写直连官方服务的脚本，也不要批量枚举、并发扫描、自动轮询或定时请求。支持的客户端与操作以官方最新文档为准。

## 连接

1. 用户在 https://open.mcd.cn/mcp 自行登录，阅读并接受最新协议，激活Token。
2. 按 https://github.com/M-China/mcd-mcp-server 中当前客户端接入教程，在其本地MCP设置连接 `https://mcp.mcd.cn`，使用Streamable HTTP与Bearer鉴权。
3. 本仓库 mcp-config.example.json 只含 `${MCD_MCP_TOKEN}`；WorkBuddy环境变量展开方式可能不同，按WorkBuddy官方说明设置本地环境/秘密存储。不要在聊天里发送Token，也不要上传真实配置。
4. 在WorkBuddy界面检查连接状态和已发现的工具。读取当前 inputSchema，参数名字、枚举、门店/餐品/券编码全部以实际schema和上游结果为准。

## 用户请求触发的流程

用户提出具体点餐需求 → 确定位置/门店和方式 → 查询相关菜单和套餐详情 → 查适用券 → 对用户要比较的具体方案试算 → 转成内部数据契约 → 离线比较。

工具可能返回 text content 或 structuredContent，WorkBuddy依据真实字段读取最后应付金额。解析不了则停止，不猜结构。纯文本错误、isError=true 或缺少最终应付价不能进入候选。无优惠券可用时走无券路径。

在项目 private/ 保存由真实返回结果转换的 candidates.json，然后从项目根目录运行：

```powershell
python skills/mcd-regret-less/scripts/planner.py compare private/candidates.json
```

Python不会发网络请求。内部items是展开后的到手餐品，另在private/保存官方下单编码、套餐选项与用券映射，不能拿展开组成当下单参数。call_ref必须对应真实WorkBuddy调用或本地记录；脚本不能验证引用真实性，人工核对真实结果。

## 最小真实验收

- 成功连接，并在WorkBuddy发现 query-meals、query-meal-detail、query-store-coupons、calculate-price。
- 用户选择一个具体门店与方式，发起普通单人点餐请求。
- 查询相关菜单、套餐详情与适用券，无券也可验收。
- 按用户具体比较请求获取原单及少量方案报价。不要写脚本批量执行。
- live比较输出与实际最终金额逐项一致。
- 用户明确「可乐不要动」后保留其他偏好重新比较；需要改商品的方案重新试算。
- 把真实日期、工具名、脱敏需求、最终金额与验收结果写入MCP_INTEGRATION.md；原始数据不发布。

此验收不需要下单。演示时不创建订单、领券或消耗积分。真正下单请求须在具体方案、门店、方式、金额展示后获得授权，再由WorkBuddy重新试算并创建；变化时再次确认。创建超时不自动重试，先查询核实是否成功。

## 脱敏摘要

公开摘要只列日期、工具名、匿名候选标识、金额和比较结果，去掉Token、手机号、完整地址、账户标识、券码、订单号及支付链接。不要把演示数据改成live伪装真实联调，不将引用字段存在视为真实调用证明。

连接成功与业务验收分别记录；完成上述项目后才能据实更新参赛材料。实际项目状态以仓库MCP_INTEGRATION.md为准。
