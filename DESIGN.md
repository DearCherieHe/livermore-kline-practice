# 设计说明

## 目标

这个项目不是行情看盘器，而是“行情手抄训练器”：

1. 让使用者亲手输入时间、开盘、最高、最低、收盘、成交量。
2. 输入后才把这一根 K 线画到画布上。
3. 通过时间线回到任一历史节点，只看当时已经出现的信息。
4. 用播放功能重走行情，训练对价格、量、节奏和关键点的感觉。

## 调研结论

- 利弗莫尔早期做过 board boy，工作内容包括从 ticker tape 把股票报价抄到黑板上，这也是本工具采用“手动记录”而不是自动拉行情的原因。
- K 线与 OHLC 图核心字段都是 open、high、low、close；成交量适合作为下方柱状辅助观察。
- TradingView Lightweight Charts 已经有完整 CandlestickSeries，但本项目刻意使用 Canvas 自绘，保留“落笔”的练习感，并避免联网依赖。
- Canvas 2D 的 `fillRect`、`lineTo`、`stroke` 足够完成蜡烛实体、影线、网格和成交量柱。

## 当前功能边界

- 本地静态网页，无后端。
- localStorage 保存练习数据。
- JSON 导入导出。
- 时间线 slider 和时间点 select 可回到任一历史节点。
- 播放只按记录顺序逐根推进。

## 下一步可以加

- 删除当前 K 线和撤销上一步。
- 手绘校验模式：先给原始报价，隐藏标准图，让使用者用鼠标画，再对比误差。
- 复盘题库：导入真实历史 OHLCV，但只逐根揭示。
- 关键点标注：突破、放量、失败、回踩、转强。
- 每日训练记录：统计录入根数、复盘次数、错判类型。

## 参考

- https://www.investopedia.com/terms/j/jesse-l-livermore.asp
- https://tradingview.github.io/lightweight-charts/docs/series-types
- https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/fillRect
- https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/lineTo
- https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/stroke
