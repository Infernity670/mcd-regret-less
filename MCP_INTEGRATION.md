# 麦当劳 MCP 集成

## 状态（2026-10-10）

本地 Skill 和离线比较器已实现，并已完成**第一轮真实场景验收**（到店自取，单人，预算 30 元，主餐硬约束）。真实调用覆盖时间对齐、门店选择、菜单、套餐详情、门店券与逐个试算；比较结果与试算金额逐项一致。

已发现两处必须在真实调用中才能暴露的口径问题，见「首轮真实证据」。

尚未验证：外送场景（delivery-query-addresses / delivery-query-stores）、下单路径（create-order）、优惠券非空路径。Token 只留本地环境变量，公开摘要已脱敏。

## Server

官方远程服务 `https://mcp.mcd.cn`，Streamable HTTP，`Authorization: Bearer ${MCD_MCP_TOKEN}`。Token只在本地环境中使用。[官方接入文档](https://github.com/M-China/mcd-mcp-server)。

## 集成工具与价值

| 官方工具 | Skill 如何使用 | 真实验证状态 |
|---|---|---|
| now-time-info | 对齐实际时间、报价新鲜度 | 已验证（2026-10-10，GMT+08:00） |
| query-nearby-stores | 用户选择可用门店，固定比较上下文 | 已验证（searchType=1 收藏门店，beType=1） |
| delivery-query-addresses / delivery-query-stores | 仅在外送请求时确定配送上下文 | 未联调，外送场景待补 |
| query-meals | 确认该门店实际可售商品 | 已验证（返回分类 + 餐品映射表，含菜单价） |
| query-meal-detail | 获取套餐组成和真实替换选项 | 已验证（套餐 rounds/choices、isDefault、diffPrice、modification） |
| query-store-coupons / query-my-coupons | 核实本次消费适用的优惠 | 已验证，本次返回空券（无券路径） |
| calculate-price | 对原单及候选逐个获取最终应付金额 | 已验证，核心；6 个候选金额与比较器逐项一致 |
| create-order | 仅WorkBuddy在具体方案获用户授权且重新试算后调用 | 未验证，本轮不下单，Python不支持 |

## 调用流程

需求 → 固定门店/方式/时间 → 菜单与套餐详情 → 可用券 → 原单与候选分别试算 → WorkBuddy按真实字段转成内部契约 → planner过滤与比较 → 用户看到金额及取舍 → 修改偏好或确认。

每个候选保留报价时间、门店/方式和真实调用引用。内部 items 是展开后的到手餐品；实际下单仍使用官方餐品编码、套餐替换选项和券参数。价格有效窗口最多5分钟；结算前重新试算。

## 技术边界

公开文档只给出工具用途，没有完整参数。因此 WorkBuddy 在WorkBuddy中读取实际工具 schema，再用真实上游标识调用。工具错误不作为报价。服务规则禁止脚本、爬虫及自动化调用，本项目不包含直连官方服务的网络脚本；MCP传输、鉴权和协议兼容由WorkBuddy负责。交互围绕用户请求的少量具体方案，不执行批量枚举或自动重试。首轮到店自取已记录验收，其他场景按实际验证范围披露。

## 首轮真实证据（脱敏）

**日期与时区**：2026-10-10 10:37–10:40，GMT+08:00
**门店与方式**：上海某门店（到店自取，beType=1 / orderType=1，不传 beCode；门店编码仅存 private/）
**输入需求（脱敏）**：单人到店取餐，想吃主餐+中薯条+中杯可乐，预算 30 元，主餐为硬约束（不可替换）。
**实际调用工具**：now-time-info、query-nearby-stores、query-meals、query-meal-detail、query-store-coupons、calculate-price（共 6 类；详细与价格试算按用户具体方案逐个执行，未批量枚举、未写网络脚本、未下单/领券/兑换积分）。
**优惠券**：该门店到店自取可用券为 0 张 → 走无券路径。

候选与最终应付金额（匿名标识，单位元）：

| 候选 | 到手餐品 | 最终应付 |
|---|---|---:|
| original（原单基准，单品拆分） | 主餐+中薯条+中杯可乐 | 50.50 |
| combo-3pc | 主餐+中薯条+中杯可乐（套餐） | 37.50 |
| combo-4pc | 主餐+中薯条+麦乐鸡4块+中杯可乐 | 59.00 |
| burger-fries | 主餐+中薯条 | 40.50 |
| burger-coke | 主餐+中杯可乐 | 36.50 |
| burger-only | 主餐 | 26.50 |

比较结果（planner.py compare，live 模式，valid_candidate_count=6，excluded=[]）：

| 方案 | 内容 | 最终价 | 相对原单 | 预算差 |
|---|---|---:|---:|---:|
| 按你的心意 | 主餐+中薯条+中杯可乐 | 37.50 | 省 13.00 | 超 7.50 |
| 小改一下 | 主餐 | 26.50 | 省 24.00 | 达标 |
| 预算优先 | 主餐 | 26.50 | 省 24.00 | 达标 |

小改一下与预算优先指向同一候选，按事实合并，不补造第三类。30 元内没有任何同时保住主餐+中薯条+中杯可乐的已核验方案：最低全配方案 37.50 元，差额 7.50 元。

**一致性核对**：comparator 读入的 total_cents 取自 calculate-price 返回的 `data.price`（单位分），6 个候选的比对金额与试算金额逐个完全相同，无四舍五入差异（均为整数分，无两位小数以上情况）。

**字段映射 / 运行问题（真实调用才暴露）**：

1. **菜单价 ≠ 实付价**：候选 combo-4pc 在 query-meals 中 currentPrice 为 32 元（标注「随单购麦金卡优惠」且 canWithOrder=true、withOrder.membershipCode=106），但 calculate-price 在不随单购时返回 `price=5900` 分，即实付 59 元。若直接用菜单价建候选，会得出 32 元这一错误报价，并由它错误地胜出。→ 印证契约中「total_cents 必须取最终应付，不使用原价/菜单价」，且必须先核实适用条件；不默认购买会员卡。
2. **单品规格需经 roundList 传递**：单品「可乐」（productCode 9900008751）默认规格是可乐**小杯**（choice 3000），中杯是同商品的选项 3050（+0.5 元）。单独传 productCode 只能得到小杯口径。本轮以 `roundList=[{round:"1", comboItemList:[{code:"3050", quantity:1}]}]` 传入，服务端正确按 1000 分计价。→ 印证「饮料规格不是同一商品」；内部 items 必须按规格区分，下单又必须还原为原 productCode + roundList。
3. **套餐默认搭配可直接映射**：套餐 combo-3pc 的三个 round 的 isDefault=1 选项恰好是「主餐 + 中薯条 4810 + 可乐中杯 3050」，与用户需求逐项一致，因此「按你的心意」无需任何替换即成立。
4. **1+1 随心配不可用于本需求**：人气经典随心配（14.9 元）蓝区默认双层吉士汉堡，候选池不含巨无霸，无法满足硬约束，直接排除，不因价格低而纳入。
5. **live 模式不接受 --now**：planner 对 live 输入强制使用系统当前时间，300 秒新鲜度窗口内比较成功，无候选因过期被排除。时间对齐依赖 now-time-info。
6. 到店自取（beType=1）确实不需要 beCode；query-nearby-stores 返回的 beCode 为空，按 schema 不传，调用未报错。

**未做的操作**：未下单、未领券、未兑换积分、未消耗积分；未批量枚举菜单；未编写直连官方服务的网络脚本。原始响应与真实编码映射只在 private/。

