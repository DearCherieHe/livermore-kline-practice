# QuantDinger 买卖点标记：从源码到可运行策略

## 1. 先看一根具体 K 线

假设第 120 根 K 线满足开多条件。QuantDinger 里必须同时发生两件事：

```python
df["open_long"].iloc[120] == True
output["signals"][0]["data"][120] == df["low"].iloc[120] * 0.995
```

第一行是“执行事实”：回测器会在策略的成交时机配置下处理开多。第二行是“显示事实”：图表在该 K 线低点下方画一个标记。只写第二行不会成交。

## 2. 源码证据链

### 2.1 作者契约

`backend_api_python/app/services/indicator_workspace.py` 的 `get_indicator_authoring_contract()` 要求新指标包含四列：

```python
df["open_long"]
df["close_long"]
df["open_short"]
df["close_short"]
```

### 2.2 校验器

`backend_api_python/app/services/indicator_validation.py` 会执行指标代码，并检查：

- 四路执行列全部存在；
- 每条 plot 和 signal 的 `data` 长度都等于 `len(df)`；
- `output` 是字典并包含图表数据。

如果只有 `output["signals"]` 而没有四路执行列，它会返回 `MissingExecutionColumns`。

### 2.3 回测器

`backend_api_python/app/services/backtest.py` 的 `_execute_indicator()` 最终从执行后的 dataframe 读取四路布尔列。`output["signals"]` 不在成交提取逻辑里。

这三份证据互相吻合，所以这是平台契约，不是示例代码的偶然写法。

## 3. 四种动作如何画在图上

QuantDinger 图表标记的 `type` 只有 `buy` 与 `sell`，四种交易动作要靠 `text` 区分：

| 执行动作 | 图表 type | text | 建议位置 |
|---|---|---|---|
| `open_long` | `buy` | 开多 | K线低点下方 |
| `close_long` | `sell` | 平多 | K线高点上方 |
| `open_short` | `sell` | 开空 | K线高点上方 |
| `close_short` | `buy` | 平空 | K线低点下方 |

可复制的标记函数：

```python
def marker_values(signal, price, multiplier):
    return [
        float(price.iloc[i]) * multiplier if bool(signal.iloc[i]) else None
        for i in range(len(df))
    ]

open_long_marks = marker_values(df["open_long"], df["low"], 0.995)
close_long_marks = marker_values(df["close_long"], df["high"], 1.005)
open_short_marks = marker_values(df["open_short"], df["high"], 1.005)
close_short_marks = marker_values(df["close_short"], df["low"], 0.995)

output = {
    "name": my_indicator_name,
    "plots": [],
    "signals": [
        {"type": "buy", "text": "开多", "data": open_long_marks, "color": "#00E676"},
        {"type": "sell", "text": "平多", "data": close_long_marks, "color": "#FFAB40"},
        {"type": "sell", "text": "开空", "data": open_short_marks, "color": "#FF5252"},
        {"type": "buy", "text": "平空", "data": close_short_marks, "color": "#40C4FF"},
    ],
}
```

不要使用 `series.where(signal, None).tolist()` 生成标记。项目的代码质量检查专门提示这种写法，因为 pandas 可能把 `None` 转成 `NaN`，导致图表序列的 JSON 表现不稳定。显式列表推导会保留真正的 `None`。

## 4. 为什么标记画在信号 K，而成交可能在下一根 K

默认语义通常是：

1. 当前 K 线收盘后确认条件；
2. 在当前 K 线上画信号标记；
3. 下一根 K 线开盘执行成交。

所以“信号点位”与“成交价格”不是同一个概念。图上箭头回答的是“策略何时作出决定”，成交明细回答的是“引擎最后以什么价格成交”。检查策略时两者都要看。

## 5. 100 个策略不能强行使用同一种运行形态

### A. 单标的 OHLCV 策略

可以直接写成 `IndicatorStrategy`，生成四路执行列和四组标记。例如 A13 涨停后缩量平台突破。

### B. 截面选股/选币策略

应使用 QuantDinger 的 Cross-Sectional Strategy：输入是 `data = {symbol: df}`，输出是 `scores`。它负责组合调仓，不等同于单标的 `output["signals"]`。

### C. 外部事件或基本面策略

财报、公告、分析师、期权、链上等字段当前没有进入 IndicatorStrategy 的默认 OHLCV dataframe。正确顺序是先定义 point-in-time 数据列并接入，再计算四路信号。不能用 RSI 或均线冒充这些数据。

### D. 多腿套利策略

资金费率、跨交易所、三角套利、并购对冲等策略需要同时记录多条腿。单张 K 线上的一个买点无法证明组合已经完整成交，需要多腿执行器和组合级审计。

## 6. 已实现的完整示例

`strategies/A13_limit_up_volume_contraction_breakout.py` 已包含：

- 涨停事件识别；
- 等待与缩量条件；
- 放量突破开多；
- 跌破事件中点或放量滞涨平多；
- 四路执行列；
- 开多、平多、开空、平空四组图表标记；
- 无未来函数的边缘触发。

本地校验：

```bash
/Users/serena/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  QuantDinger_Strategy_Library/tools/validate_indicator_file.py \
  QuantDinger_Strategy_Library/strategies/A13_limit_up_volume_contraction_breakout.py
```

看到 `PASS` 表示代码结构、执行列、序列长度和标记值通过本地契约检查。之后仍需在 QuantDinger 的 `verifyCode` 和真实回测中复核，因为本地样本不能替代平台的数据源与成交引擎。
