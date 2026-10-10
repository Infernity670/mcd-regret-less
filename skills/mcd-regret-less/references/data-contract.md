# 内部数据契约 v0.1

此契约由WorkBuddy 把真实 MCP 结果转换得到，不是官方 API 参数。转换需要逐项检查真实餐品编码、套餐展开组成和最后应付金额，不自动推断未记录字段。

## compare 输入

```json
{
  "mode": "live",
  "context": {"store_id": "运行时实际门店标识", "dining_mode": "运行时就餐方式"},
  "preferences": {
    "budget_cents": 3000,
    "required": {"实际餐品规格标识": 1},
    "desired": {"实际餐品规格标识": 1},
    "forbidden": [],
    "weights": {}
  },
  "baseline_id": "original",
  "max_quote_age_seconds": 300,
  "candidates": []
}
```

context 至少包含 store_id 与 dining_mode；外送附去标识化的地址关联标识，预约附预约时间。所有候选 context 必须完全一致。候选 id 唯一，离线比较器最多接受100个已存在记录，此上限不是对官方服务进行批量调用的许可。WorkBuddy只围绕用户请求比较少量具体方案。

候选对象字段：

| 字段 | 含义 |
|---|---|
| id | 本次比较中的候选标识；不是官方餐品编码 |
| items | 用户实际收到的每种餐品规格及正整数数量，展开套餐；编码准确匹配同一个规格 |
| total_cents | 最终应付人民币整数分，含实际费用，不使用原价/单项小计 |
| source | live 为 mcd-mcp，demo 为 demo |
| quoted_at | 获取报价时的 ISO 8601 时间，必须带时区 |
| context | 与本次比较完全相同的上下文 |
| evidence | live 必需：tool=calculate-price，call_ref=真实WorkBuddy调用引用或 private/ 内该响应记录引用 |
| available | 若官方明确不可售则 false，不得把未知状态假装可售 |
| is_error | 工具错误时 true，不参与比较 |

call_ref 只能记录可追溯的真实调用。脚本检查字段存在，但不会联网认证或验证记录真实性；实际审核由使用者核对原始结果。不把引用存在等同于证明已经真实调用。

将最终金额转分的示例：`amount = Decimal(str(actual_amount)); cents = amount * 100`。确认 amount 非负有限、cents 是整数，再用 `int(cents)`；不要用 `int(float(amount) * 100)`。若原字段已经是分则直接保留，切勿再次乘100。

## 算法

先排除无效金额、错误/失效/混合来源/上下文不符/缺少依据/不满足硬偏好/命中禁选项的候选。5分钟只是本地新鲜度窗口，不是官方价格保证。服务端可用状态必须由WorkBuddy核验。

损失分 = Σ max(0,期望数量−实际数量) × 该餐品权重。新增餐品不抵消损失，新增数量单独列出。required 与 desired 按更大的数量组成比较目标。

- keep：损失0的有效候选中最低价，可超预算并展示差额。
- small_change：预算内损失大于0的候选中先最小损失，再最低价；属于改动方案，不保证只改一项。
- budget：预算内有效候选中先最低价，再最小损失。
- 同价同损失按候选 id 排序，保证重复运行结果稳定。
- minimum_gap_cents：有效候选中最低应付价与预算的非负差；没有有效候选为 null。
- savings_cents：有效原单金额−候选金额，可以为负；缺少有效基准为 null。

三类可能重复或为空，WorkBuddy按事实合并或说明，不补造报价。

## 增量更新

`update` 接收旧 preferences JSON 与 patch JSON。budget_cents/forbidden 覆盖对应字段；required/desired/weights 按键合并，0表示明确删除。输出新对象，不改原文件。解除硬偏好不会自动删掉同名软偏好，用户明确不想吃时同时移除 desired。

## 本地隐私

真实 candidates、调用参数、订单映射和输出写入 private/，不进入 GitHub/压缩包。候选脚本输出可能含用户餐品偏好，发布时人工审阅脱敏。演示夹中的所有数据均为虚构。
