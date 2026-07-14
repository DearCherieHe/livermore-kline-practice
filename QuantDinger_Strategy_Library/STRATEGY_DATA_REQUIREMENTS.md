# QuantDinger 100 个策略数据需求、来源与导入指南

> 版本：2026-07-15。本文与 `README.md` 中 A01-A35、U01-U35、C01-C30 一一对应。来源名称是可选方案，不代表免费、永久可用或已获得许可；正式使用前必须确认 API 条款、地区限制、授权和费用。

## 1. 先回答：每个策略都需要不同数据吗？

不完全是。100 个策略共享约 40 个底层数据族。真正不同的是：

- 使用哪些字段；
- 字段组合成什么信号；
- 数据在什么时间才对市场可见；
- 单标的、截面组合还是多腿交易；
- 更新频率和允许的最大延迟。

一个正确的数据系统应该是：数据采集器复用，策略逻辑独立。不要为每个策略复制一套行情下载代码。

## 2. QuantDinger 当前边界

QuantDinger 的 `BaseDataSource.get_kline()` 当前把行情统一成：

```python
{"time": 1710000000, "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 1000.0}
```

单标的 `IndicatorStrategy` 默认只收到 OHLCV。它的沙盒禁止网络、文件和数据库访问。因此以下写法是错误方向：

```python
# 不要放进 IndicatorStrategy
requests.get("https://some-provider/api")
pd.read_csv("fundamentals.csv")
```

外部数据必须在沙盒外采集，保存后由回测/实盘数据装配层加入 dataframe：

```text
公开或授权数据源
      ↓  ETL采集、标准化、去重
feature_observations
      ↓  按 available_at 做 point-in-time join
OHLCV + 外部特征 dataframe
      ↓
IndicatorStrategy → 四路执行信号 → 图表标记
```

当前仓库已有 OHLCV、A/H 基本面、新闻、宏观、情绪等 provider，但它们还没有统一注入 IndicatorStrategy。本文中的“需新增装配器”表示数据抓取可能已有基础模块，但策略沙盒尚不能直接使用。

## 3. 外部特征统一数据契约

建议所有外部数据先保存成长表：

| 字段 | 含义 |
|---|---|
| `market` | `CNStock`、`USStock`、`Crypto` |
| `symbol` | 平台规范化后的标的代码 |
| `feature_name` | 如 `eps_surprise_z` |
| `value` | 数值、布尔或短字符串 |
| `event_time` | 经济事件实际所属时间 |
| `available_at` | 数据首次可被交易者获知的时间 |
| `ingested_at` | 本系统抓取时间 |
| `source` | 数据提供方 |
| `revision_id` | 修订版本，可为空 |

回测连接必须使用 `available_at`，不能使用财报所属季度末日期：

```python
def point_in_time_join(bars, features):
    left = bars.sort_values(["symbol", "time"])
    right = features.sort_values(["symbol", "available_at"])
    return pd.merge_asof(
        left,
        right,
        by="symbol",
        left_on="time",
        right_on="available_at",
        direction="backward",
        allow_exact_matches=True,
    )
```

这一步的目的，是保证 2024 年 3 月的回测只能看到 2024 年 3 月当时已经发布的数据。

## 4. 40 个可复用数据族

| 编号 | 数据族 | 主要字段 | 可选来源 | 当前状态 | 导入样例 |
|---|---|---|---|---|---|
| D01 | 标准 OHLCV | time/open/high/low/close/volume | QuantDinger DataSourceFactory；腾讯、Twelve Data、yfinance、AkShare、CCXT | 已有 | I01 |
| D02 | 逐笔、盘口、集合竞价 | bid/ask、深度、主动买卖、竞价量、VWAP | 交易所授权行情；Wind/Choice/iFinD；Polygon/Databento；券商行情 | 需新增 | I02 |
| D03 | 交易状态与市场日历 | 涨跌停、停牌、LULD、交易日、复牌时间 | 上交所/深交所、NYSE/Nasdaq、交易所日历 | 需增强 | I03 |
| D04 | A股公告与事件 | 预告、快报、政策、ST、减持、员工持股 | 巨潮资讯、交易所公告、Tushare、AkShare、Wind | 部分已有新闻 | I04 |
| D05 | A/H 财务报表 | 营收、利润、现金流、资产、存货、应收 | 本仓库 cn_hk_fundamentals；Twelve Data、AkShare、Tushare、Wind | 已有抓取，需注入 | I05 |
| D06 | 分析师一致预期 | EPS/营收预测、目标价、修正人数、离散度 | Finnhub、FactSet、Refinitiv、Bloomberg、Wind/Choice | 需授权或新增 | I06 |
| D07 | 公司行动与资本运作 | 分红、回购、定增、股本、员工计划 | 交易所公告、Tushare、AkShare、SEC | 需新增 | I07 |
| D08 | A股资金与持仓 | 两融、龙虎榜、公募持仓、大宗交易 | 交易所、Tushare、AkShare、Wind/Choice | 需新增 | I08 |
| D09 | 指数规则与成分 | 成分、权重、调整公告、生效日 | 中证/国证、S&P DJI、Nasdaq、MSCI、交易所 | 需新增 | I09 |
| D10 | ETF/基金数据 | 份额、申赎、PCF、NAV、持仓、资金流 | 基金公司、交易所、Wind、ETF官网、Nasdaq | 需新增 | I10 |
| D11 | 行业、供应链与暴露 | 行业分类、客户供应商、收入暴露 | 年报、SEC 10-K、FactSet Revere、Bloomberg SPLC、CSMAR | 需新增 | I11 |
| D12 | A/H与外汇配对 | A价、H价、汇率、股息、交易时段 | QuantDinger A/H OHLCV、外汇源、公司行动 | OHLCV已有，需配对 | I12 |
| D13 | 可转债 | 转债价格、正股、转股价、溢价、赎回条款 | 集思录、交易所、Wind/Choice、AkShare | 需新增 | I13 |
| D14 | IPO与限售解禁 | 发行价、上市日、限售股、解禁日、股东类型 | 交易所、招股书、Tushare、Wind、SEC | 需新增 | I14 |
| D15 | SEC/XBRL公司财务 | companyfacts、10-K/10-Q、分部与客户披露 | SEC EDGAR 官方 API | 需新增 | I15 |
| D16 | 美股财报与日历 | actual/estimate、surprise、guidance、earnings date | Finnhub、Nasdaq、SEC、FactSet、yfinance | 部分已有库 | I16 |
| D17 | Form 4内部人交易 | owner、role、transaction code、shares、price | SEC EDGAR Form 4、Finnhub | 需新增 | I17 |
| D18 | 13D/13G维权持仓 | filer、持股比例、目的、修订、出售 | SEC EDGAR Schedule 13D/13G | 需新增 | I18 |
| D19 | 美股股本与回购 | diluted shares、issuance、repurchase、buyback authorization | SEC XBRL、公司公告、Nasdaq | 需新增 | I19 |
| D20 | 股票/指数期权 | IV曲面、delta、skew、OI、volume、Greeks | OPRA授权商、CBOE、Polygon、Tradier、IBKR、yfinance延迟数据 | 需新增 | I20 |
| D21 | 做空与借券 | short interest、borrow fee、utilization、availability | FINRA、Nasdaq、S3、Ortex、IBKR | 需新增 | I21 |
| D22 | 信用与公司债 | bond price、OAS、yield、CDS、TRACE成交 | FINRA TRACE、FRED、ICE/Bloomberg/Refinitiv | 需新增 | I22 |
| D23 | 新闻、文本与关注度 | 新闻情绪、电话会、搜索、Wikipedia、事件去重 | 本仓库 news provider、Finnhub、SEC、GDELT、Google Trends、Wikimedia | 部分已有 | I23 |
| D24 | 宏观与波动环境 | 利率曲线、实际利率、信用利差、VIX期限、期指 | 本仓库 MacroSeries/FRED、CBOE、CME、Treasury | 部分已有 | I24 |
| D25 | 美股特殊公司事件 | 分拆、并购、拆股、LULD、监管、投票 | SEC、公司公告、FTC/DOJ、交易所、Nasdaq | 需新增 | I25 |
| D26 | 机构与基金持仓 | 13F、基金风格、市值约束、税损代理 | SEC 13F、基金披露、Morningstar、FactSet | 需新增 | I26 |
| D27 | 加密现货/合约微观行情 | OHLCV、L2、成交、跨所价格 | QuantDinger CCXT、交易所公开 WebSocket/API | OHLCV已有，L2需新增 | I27 |
| D28 | 永续与期货衍生品 | funding、basis、OI、liquidation、mark/index price | CCXT、Binance/OKX/Bybit、CoinGlass、Kaiko | 需新增 | I28 |
| D29 | 加密期权 | IV、skew、OI、Greeks、expiry、strike | Deribit、OKX、CME、Amberdata、Kaiko | 需新增 | I29 |
| D30 | 链上估值与币龄 | realized cap、MVRV、SOPR、HODL waves、CDD | Glassnode、Coin Metrics、CryptoQuant、自建节点 | 需新增 | I30 |
| D31 | 地址标签与交易所流量 | exchange inflow/outflow、whale、miner/entity labels | Glassnode、CryptoQuant、Arkham、Nansen、自建标签 | 需新增 | I31 |
| D32 | 挖矿与网络安全 | hash rate、difficulty、hash price、miner reserve | Coin Metrics、Glassnode、Blockchain.com、矿池 | 需新增 | I32 |
| D33 | 质押、发行与解锁 | staking、validator queue、unlock schedule、emission | 链上节点、TokenUnlocks、项目官方文档、Messari | 需新增 | I33 |
| D34 | 稳定币 | supply、mint/burn、reserves、redemption、pool price | 链上、发行方证明、Coin Metrics、DefiLlama | 需新增 | I34 |
| D35 | DEX、AMM与mempool | pool reserves、swap、LP ranges、gas、mempool | The Graph、自建节点、Dune、Etherscan、DEX subgraph | 需新增 | I35 |
| D36 | DeFi基本面 | TVL、fees、revenue、incentives、active users | DefiLlama、Token Terminal、Dune、链上事件 | 需新增 | I36 |
| D37 | 链上治理 | proposal、vote、quorum、delegation、execution | Snapshot、Tally、Governor合约、项目论坛 | 需新增 | I37 |
| D38 | 交易容量与资产可用性 | fee、withdrawal、borrow、balance、lot size、latency | CCXT、交易所账户API、托管系统 | 部分已有交易适配器 | I38 |
| D39 | 专利与研发产出 | patent family、citation、assignee、技术分类 | USPTO PatentsView、Google Patents、EPO OPS | 需新增 | I39 |
| D40 | 封闭式基金 NAV | NAV、market price、distribution、discount | 基金官网、CEFConnect、Morningstar、交易所 | 需新增 | I40 |

## 5. 导入样例库

这些代码运行在后端 ETL 或独立同步脚本中，不放进 IndicatorStrategy。示例只展示最小读取和标准化方式；生产环境还要加超时、重试、限频、缓存、数据质量检查和授权管理。

仓库当前 requirements 已包含 `requests`、`yfinance`、`ccxt`、`akshare` 等；`tushare`、`exchange_calendars` 以及部分授权供应商 SDK 需要按你最终选择的数据源另行安装。示例中的 `PROVIDER_PCF_URL`、账户密钥和授权 CSV 是占位输入，不是现成凭证。

### I01：QuantDinger 内置 OHLCV（D01）

```python
from app.data_sources.factory import DataSourceFactory

rows = DataSourceFactory.get_kline(
    market="CNStock", symbol="600519", timeframe="1D", limit=500
)
bars = pd.DataFrame(rows)
```

### I02：逐笔/盘口供应商 CSV 或 API（D02）

```python
raw = pd.read_csv("licensed_ticks.csv")
ticks = raw.rename(columns={"ts": "event_time", "px": "price", "qty": "size"})
ticks["event_time"] = pd.to_datetime(ticks["event_time"], utc=True)
ticks["available_at"] = ticks["event_time"]
```

### I03：交易日历与状态（D03）

```python
import exchange_calendars as xcals

calendar = xcals.get_calendar("XNYS")
schedule = calendar.schedule.loc["2024-01-01":"2025-12-31"].reset_index()
# A股涨跌停、停牌和美股LULD仍应另接交易所状态数据。
```

### I04：A股公告（D04）

```python
import akshare as ak

ann = ak.stock_notice_report(symbol="全部", date="20250115")
ann = ann.rename(columns={"代码": "symbol", "公告标题": "title", "公告时间": "available_at"})
```

### I05：A/H基本面（D05）

```python
from app.data_sources.cn_hk_fundamentals import fetch_cn_financial_statements

payload = fetch_cn_financial_statements("sh600519")
# 保存原始报表，同时记录公告时间 available_at；不要只保存报告期。
```

### I06：分析师一致预期（D06）

```python
import os, requests

rows = requests.get(
    "https://finnhub.io/api/v1/stock/eps-estimate",
    params={"symbol": "AAPL", "token": os.environ["FINNHUB_API_KEY"]},
    timeout=20,
).json().get("data", [])
estimates = pd.DataFrame(rows)
```

### I07：分红、回购、定增等公司行动（D07）

```python
import tushare as ts

pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
dividend = pro.dividend(ts_code="600519.SH")
repurchase = pro.repurchase(ts_code="600519.SH")
```

### I08：两融、龙虎榜、大宗与基金持仓（D08）

```python
margin = pro.margin_detail(ts_code="600519.SH", start_date="20250101", end_date="20251231")
top_list = pro.top_list(trade_date="20250115")
block = pro.block_trade(ts_code="600519.SH", start_date="20250101", end_date="20251231")
```

### I09：指数成分与权重（D09）

```python
weights = pro.index_weight(index_code="000300.SH", start_date="20250101", end_date="20251231")
weights = weights.rename(columns={"trade_date": "event_time", "con_code": "symbol", "weight": "index_weight"})
```

### I10：ETF/基金份额、PCF与NAV（D10）

```python
import requests

pcf_text = requests.get(PROVIDER_PCF_URL, timeout=20).text  # 使用基金公司公开PCF地址
pcf = parse_provider_pcf(pcf_text)  # 适配器内统一 symbol、weight、cash_substitution
```

### I11：行业、客户与供应链（D11）

```python
relationships = pd.read_csv("licensed_supply_chain.csv")
relationships = relationships.rename(columns={
    "company": "symbol", "related_company": "peer_symbol", "revenue_pct": "exposure"
})
relationships["available_at"] = pd.to_datetime(relationships["filing_date"], utc=True)
```

### I12：A/H与汇率配对（D12）

```python
a = pd.DataFrame(DataSourceFactory.get_kline("CNStock", "601318", "1D", 500))
h = pd.DataFrame(DataSourceFactory.get_kline("HKStock", "02318", "1D", 500))
fx = pd.DataFrame(DataSourceFactory.get_kline("Forex", "CNYHKD", "1D", 500))
pair = a.merge(h, on="time", suffixes=("_a", "_h")).merge(fx[["time", "close"]], on="time")
```

### I13：可转债（D13）

```python
import akshare as ak

cb = ak.bond_zh_hs_cov_spot()
cb = cb.rename(columns={"symbol": "bond_symbol", "trade": "bond_price"})
# 转股价、赎回/下修条款应从交易所公告或授权数据补齐。
```

### I14：IPO与解禁（D14）

```python
new_share = pro.new_share(start_date="20240101", end_date="20251231")
float_schedule = pro.share_float(ts_code="301000.SZ", start_date="20240101", end_date="20261231")
```

### I15：SEC Company Facts（D15）

```python
import requests

headers = {"User-Agent": "YourName research@example.com"}
facts = requests.get(
    "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    headers=headers, timeout=30,
).json()
```

### I16：美股财报与日历（D16）

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
earnings_dates = ticker.get_earnings_dates(limit=24).reset_index()
calendar = ticker.calendar
```

### I17：Form 4内部人交易（D17）

```python
submissions = requests.get(
    "https://data.sec.gov/submissions/CIK0000320193.json", headers=headers, timeout=30
).json()
recent = pd.DataFrame(submissions["filings"]["recent"])
form4 = recent.loc[recent["form"].eq("4")]
```

### I18：13D/13G（D18）

```python
forms = recent.loc[recent["form"].isin(["SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"])]
forms["available_at"] = pd.to_datetime(forms["filingDate"], utc=True)
# 持股比例和目的需要继续解析对应 filing document。
```

### I19：SEC股本、发行与回购（D19）

```python
us_gaap = facts["facts"]["us-gaap"]
shares = pd.DataFrame(us_gaap["EntityCommonStockSharesOutstanding"]["units"]["shares"])
shares["available_at"] = pd.to_datetime(shares["filed"], utc=True)
```

### I20：股票期权链（D20）

```python
ticker = yf.Ticker("AAPL")
expiry = ticker.options[0]
chain = ticker.option_chain(expiry)
calls, puts = chain.calls, chain.puts  # 延迟数据；生产回测应使用历史授权快照
```

### I21：做空与借券（D21）

```python
short = pd.read_csv("licensed_short_interest.csv")
short["available_at"] = pd.to_datetime(short["publication_time"], utc=True)
short = short[["symbol", "short_interest", "borrow_fee", "utilization", "available_at"]]
```

### I22：TRACE、信用利差与CDS（D22）

```python
bonds = pd.read_csv("finra_trace_export.csv")
bonds["event_time"] = pd.to_datetime(bonds["trade_time"], utc=True)
bonds["available_at"] = bonds["event_time"] + pd.to_timedelta(bonds["dissemination_delay_sec"], unit="s")
```

### I23：新闻、电话会与关注度（D23）

```python
from app.data_providers.news import fetch_financial_news

news = fetch_financial_news(lang="all")
# 入库前按 canonical_url + 标题指纹去重，并保存首次发布时间。
```

### I24：FRED宏观序列（D24）

```python
from app.data_providers.macro_series import get_macro_series_provider

provider = get_macro_series_provider()
yield_curve = provider.fetch_fred_series("T10Y2Y")
real_yield = provider.fetch_fred_series("DFII10")
```

### I25：分拆、并购、拆股等特殊事件（D25）

```python
special = recent.loc[recent["form"].isin(["8-K", "S-4", "DEFM14A", "10-12B"])]
special["available_at"] = pd.to_datetime(special["filingDate"], utc=True)
```

### I26：13F机构持仓（D26）

```python
holdings = pd.read_csv("sec_13f_information_table.csv")
holdings["available_at"] = pd.to_datetime(holdings["filing_date"], utc=True)
# 回测不能把季度末持仓当作季度末已经公开；必须使用 filing_date。
```

### I27：CCXT现货、合约与订单簿（D27）

```python
import ccxt

exchange = ccxt.binance({"enableRateLimit": True})
ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=500)
book = exchange.fetch_order_book("BTC/USDT", limit=50)
```

### I28：资金费率、基差与持仓量（D28）

```python
swap = ccxt.binanceusdm({"enableRateLimit": True})
funding = swap.fetch_funding_rate_history("BTC/USDT:USDT", limit=500)
open_interest = swap.fetch_open_interest("BTC/USDT:USDT")
```

### I29：Deribit加密期权（D29）

```python
summary = requests.get(
    "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
    params={"currency": "BTC", "kind": "option"}, timeout=20,
).json()["result"]
options = pd.DataFrame(summary)
```

### I30：Glassnode链上估值（D30）

```python
series = requests.get(
    "https://api.glassnode.com/v1/metrics/market/mvrv",
    params={"a": "BTC", "i": "24h", "api_key": os.environ["GLASSNODE_API_KEY"]},
    timeout=30,
).json()
mvrv = pd.DataFrame(series).rename(columns={"t": "event_time", "v": "mvrv"})
```

### I31：地址标签与交易所流量（D31）

```python
flows = pd.read_csv("licensed_entity_adjusted_exchange_flows.csv")
flows["available_at"] = pd.to_datetime(flows["provider_timestamp"], utc=True)
# 必须保存标签版本；交易所地址归属会被供应商事后修订。
```

### I32：哈希率与矿工数据（D32）

```python
hashrate = requests.get("https://api.blockchain.info/charts/hash-rate?timespan=2years&format=json", timeout=30).json()
hashrate = pd.DataFrame(hashrate["values"]).rename(columns={"x": "event_time", "y": "hash_rate"})
```

### I33：质押与代币解锁（D33）

```python
unlocks = pd.read_csv("official_or_licensed_token_unlock_schedule.csv")
unlocks["event_time"] = pd.to_datetime(unlocks["unlock_time"], utc=True)
unlocks["available_at"] = pd.to_datetime(unlocks["announced_at"], utc=True)
```

### I34：稳定币供应与储备（D34）

```python
stablecoins = requests.get("https://stablecoins.llama.fi/stablecoins?includePrices=true", timeout=30).json()
assets = pd.DataFrame(stablecoins["peggedAssets"])
# 储备证明与赎回状态必须另接发行方官方披露。
```

### I35：DEX/AMM/mempool（D35）

```python
query = """{ pools(first: 100, orderBy: totalValueLockedUSD, orderDirection: desc) { id token0Price token1Price totalValueLockedUSD } }"""
payload = requests.post(SUBGRAPH_URL, json={"query": query}, timeout=30).json()
pools = pd.DataFrame(payload["data"]["pools"])
```

### I36：DefiLlama协议基本面（D36）

```python
protocol = requests.get("https://api.llama.fi/protocol/aave", timeout=30).json()
tvl = pd.DataFrame(protocol["tvl"]).rename(columns={"date": "event_time", "totalLiquidityUSD": "tvl_usd"})
```

### I37：Snapshot治理（D37）

```python
query = """query { proposals(first: 100, where: {space_in: [\"aave.eth\"]}) { id title start end scores state } }"""
result = requests.post("https://hub.snapshot.org/graphql", json={"query": query}, timeout=30).json()
proposals = pd.DataFrame(result["data"]["proposals"])
```

### I38：交易容量与借币可用性（D38）

```python
exchange = ccxt.okx({"apiKey": KEY, "secret": SECRET, "password": PASSPHRASE})
markets = exchange.load_markets()
balance = exchange.fetch_balance()
# 账户密钥只存在受控后端；绝不能传入指标代码或前端。
```

### I39：专利与引用（D39）

```python
payload = requests.get(
    "https://api.patentsview.org/patents/query",
    params={"q": '{"_eq":{"assignee_organization":"Apple Inc."}}', "f": '["patent_number","patent_date","patent_num_cited_by_us_patents"]'},
    timeout=30,
).json()
patents = pd.DataFrame(payload.get("patents", []))
```

### I40：封闭式基金NAV（D40）

```python
nav = pd.read_csv("fund_sponsor_daily_nav.csv")
nav["date"] = pd.to_datetime(nav["date"], utc=True)
nav["discount"] = nav["market_price"] / nav["nav"] - 1
```

## 6. A股策略逐项数据说明（A01-A35）

| ID | 策略 | 必需输入字段 | 数据族/来源样例 | 更新与运行形态 |
|---|---|---|---|---|
| A01 | 业绩预告超预期漂移 | forecast_low/high、prior_profit、consensus_profit、announcement_time、revision_direction | D04/I04 + D06/I06 + D05/I05 | 公告事件；单标的事件策略；以公告发布时间为 available_at |
| A02 | 快报到年报差异修正 | express_revenue/profit/margin、annual_report_values、operating_cashflow、revision_flag | D04/I04 + D05/I05 | 快报与年报事件；必须保留两次披露版本 |
| A03 | 分红惊喜与可持续性 | dividend_per_share、payout_ratio、free_cashflow、net_debt、ex_date | D07/I07 + D05/I05 | 方案公告日更新；除权日是执行事件，不可替代公告日 |
| A04 | 回购执行力度 | planned_min/max、repurchased_amount、avg_buyback_price、daily_buyback_value、ADV | D07/I07 + D01/I01 | 回购进展公告/日频；单标的 |
| A05 | 员工持股计划利益绑定 | plan_price、lockup_days、participant_roles、performance_targets、executive_departures | D04/I04 + D07/I07 | 公告事件；文本条款需结构化 |
| A06 | 定增折价吸收 | issue_price、issue_size、subscriber_type、completion_date、unlock_date、close/volume | D07/I07 + D14/I14 + D01/I01 | 完成公告后日频；解禁日前强制风险标记 |
| A07 | 大宗交易折价消化 | block_price、block_size、buyer/seller_type、reduction_notice、close、active_buy_ratio | D08/I08 + D02/I02 + D04/I04 | 大宗事件+分钟/日频；席位身份需版本化 |
| A08 | 龙虎榜机构净买入延续 | institution_net_buy、seat_concentration、limit_status、next_day_auction/volume | D08/I08 + D02/I02 + D03/I03 | 交易日收盘后；A股T+1与涨停可成交性 |
| A09 | 融资余额加速但价格未动 | financing_balance、financing_buy_value、market_cap、close、realized_vol | D08/I08 + D01/I01 | 日频；数据通常盘后公布，下一交易日才可用 |
| A10 | 指数纳入预期 | eligibility、free_float_cap、liquidity、profitability、current_membership、rule_version | D09/I09 + D01/I01 | 月/季频截面；规则版本和公告日都要保存 |
| A11 | 指数生效日收盘冲击反转 | announced_weight_change、effective_date、closing_auction_volume、close_auction_price、ADV | D09/I09 + D02/I02 | 生效日分钟级；事件驱动 |
| A12 | 首板质量筛选 | prior_limit_count、seal_time、open_count、turnover、limit_queue、catalyst、sector_breadth | D03/I03 + D02/I02 + D04/I04 + D11/I11 | 分钟级；只在可成交价生成订单 |
| A13 | 涨停后缩量平台突破 | OHLCV、limit_up_event、bars_since_event、event_mid、platform_high、volume_ratio | D01/I01 + D03/I03 | 日频单标的；已有完整实现 |
| A14 | 跌停流动性恢复反弹 | limit_down_queue、continuous_auction_status、sell_order_decay、fraud/delist_flag、sector_return | D03/I03 + D02/I02 + D04/I04 + D11/I11 | 分钟级；重大违规事件直接禁用 |
| A15 | 集合竞价失衡回归 | auction_price/volume、indicative_imbalance、sector_expected_gap、news_flag、post_open_VWAP | D02/I02 + D11/I11 + D23/I23 | 开盘竞价与分钟级；单标的相对价值 |
| A16 | 尾盘机构成交延续 | 14:30后active_buy_value、late_volume_share、order_size_distribution、rebalance_flag | D02/I02 + D09/I09 | 分钟/逐笔；当日尾盘信号、次日退出 |
| A17 | 隔夜跳空信息衰减 | open_gap、global_factor_return、sector_beta、material_news_flag、opening_volume | D01/I01 + D23/I23 + D24/I24 | 日内；新闻发布时间必须覆盖隔夜窗口 |
| A18 | AH溢价收敛 | A/H同步价格、CNYHKD、dividend、tax/borrow_cost、trading_session | D12/I12 + D07/I07 + D38/I38 | 双标的/多腿；需同步时钟和可借券检查 |
| A19 | 可转债-正股信息传导 | bond/stock price、conversion_price、conversion_premium、implied_vol、redemption/reset_terms | D13/I13 + D01/I01 + D04/I04 | 双标的；条款事件优先于价差信号 |
| A20 | ETF申赎冲击篮子 | ETF shares、creation/redemption、PCF weights、cash_substitution、component_ADV | D10/I10 + D01/I01 + D02/I02 | 截面/篮子；日内或日频 |
| A21 | 公募重仓拥挤释放 | disclosed_holdings、fund_shares、estimated_redemption、position_to_ADV、disclosure_date | D08/I08 + D10/I10 + D01/I01 | 季度+日频；使用披露日而非季度末 |
| A22 | 分析师盈利预测修正广度 | analyst_id、old/new_estimate、revision_time、target_price、dispersion、price_return | D06/I06 + D01/I01 | 事件聚合为日频；分析师去重 |
| A23 | 供应链订单扩散 | leader_order_event、supplier_link、revenue_exposure、contract_status、supplier_return | D04/I04 + D11/I11 + D05/I05 | 事件+截面；供应链关系以最近披露版本为准 |
| A24 | 政策文本产业扩散 | policy_text、issuer、budget、deadline、implementing_agency、company_revenue_exposure | D04/I04 + D11/I11 + D23/I23 | 政策事件+截面；正式原文优先于新闻摘要 |
| A25 | 财务困境摘帽重估 | ST_status、removal_application/approval、audit_opinion、operating_cashflow、one_off_profit | D04/I04 + D05/I05 + D03/I03 | 交易所事件；长停牌与涨跌停要建模 |
| A26 | 新股次新供给枯竭 | IPO_price/date、daily_turnover、volatility、platform_range、lockup_shares/unlock_date | D14/I14 + D01/I01 | 日频；上市初期和解禁窗口 |
| A27 | 质量价值复合 | FCF_yield、ROIC、net_debt、gross_margin_stability、industry、valuation_date | D05/I05 + D11/I11 | 季度截面；财报发布时间点连接 |
| A28 | 应计项目异常 | net_income、CFO、total_assets、receivables、inventory、capitalized_cost | D05/I05 | 季度截面；使用原始报表版本 |
| A29 | 毛利润率与资产效率 | revenue、COGS、gross_profit、average_assets、asset_turnover、industry | D05/I05 + D11/I11 | 季度截面 |
| A30 | 存货-收入剪刀差 | inventory_yoy、revenue_yoy、receivable_yoy、industry_inventory_cycle | D05/I05 + D11/I11 | 季度截面；行业口径固定 |
| A31 | 现金流-利润背离修复 | CFO、net_income、CFO_to_profit、two_quarter_trend、report_available_at | D05/I05 | 季度单标的/截面 |
| A32 | 行业中性残差动量 | adjusted_returns、market/industry/style_factor_returns、free_float_cap、industry | D01/I01 + D11/I11 | 日频计算、月频截面调仓 |
| A33 | 低特质波动防御 | daily_returns、factor_returns、idio_vol、profit_quality、valuation、liquidity | D01/I01 + D05/I05 + D11/I11 | 日频因子、月频截面 |
| A34 | 行业龙头-跟随者时滞 | leader/follower_map、minute_returns、information_volume、revenue_exposure、lag_correlation | D11/I11 + D02/I02 + D01/I01 | 分钟级配对/截面 |
| A35 | 同业基本面配对收敛 | pair_map、adjusted_prices、cointegration_residual、financial_exposure_distance、event_calendar | D01/I01 + D05/I05 + D11/I11 + D04/I04 | 双标的；滚动协整并在财报窗口暂停 |

## 7. 美股策略逐项数据说明（U01-U35）

| ID | 策略 | 必需输入字段 | 数据族/来源样例 | 更新与运行形态 |
|---|---|---|---|---|
| U01 | 标准化盈利惊喜漂移 | EPS_actual、consensus_snapshot、historical_error_std、guidance_change、release_time | D16/I16 + D06/I06 + D23/I23 | 财报事件；盘前/盘后时间决定首个可交易bar |
| U02 | 财报电话会语义拐点 | transcript、speaker/section、prior_transcript、certainty/risk/evasion_scores、filing_values | D23/I23 + D16/I16 + D15/I15 | 电话会结束后事件；文本版本与模型版本都要保存 |
| U03 | 盈利预期修正扩散 | company/peer estimates、analyst_id、revision_time、industry_map、coverage_count | D06/I06 + D11/I11 + D16/I16 | 日频截面；同一分析师重复修正去重 |
| U04 | 财报前预期爬升 | estimate_revision、residual_momentum、earnings_time、ATM_IV、IV_percentile | D16/I16 + D20/I20 + D01/I01 | 财报前日频；公布前平仓 |
| U05 | 财报缺口后日内延续 | release/guidance、premarket_gap、relative_volume、opening_range、VWAP | D16/I16 + D01/I01 + D02/I02 | 盘前事件+分钟级 |
| U06 | 研发转化效率 | R&D expense、patent_family/citations、new_product_revenue、gross_profit_increment | D15/I15 + D39/I39 | 季/年频截面；专利受让人名称需实体匹配 |
| U07 | 总资产增长异常 | total_assets、capex、acquisition_value、organic_growth、filing_date | D15/I15 + D25/I25 | 季/年频截面；并购单独标记 |
| U08 | 净股票发行因子 | diluted_shares、shares_outstanding、issuance、repurchase、stock_compensation | D19/I19 + D15/I15 | 季度截面；使用提交日 |
| U09 | 经营杠杆惊喜 | revenue_surprise、operating_income_surprise、fixed_cost_proxy、restructuring_charges | D15/I15 + D16/I16 | 财报事件；剔除一次性项目 |
| U10 | 客户集中度改善 | major_customer_pct、customer_count、revenue_growth、retention、contract_disclosure | D15/I15 + D11/I11 + D23/I23 | 年/季频；10-K/10-Q文本结构化 |
| U11 | 价值-动量双确认 | value_metrics、12_1_residual_momentum、industry/style_factors、liquidity | D15/I15 + D01/I01 + D11/I11 | 月频截面 |
| U12 | 低贝塔杠杆约束溢价 | daily_returns、market_return、beta、profitability、borrow/funding_cost | D01/I01 + D15/I15 + D22/I22 | 日频估计、月频截面 |
| U13 | 52周高点锚定 | adjusted_high_252、close、estimate_revision、valuation_percentile | D01/I01 + D16/I16 + D15/I15 | 日频单标的/截面 |
| U14 | 公司内部人集群买入 | Form4 owner/role、transaction_code、shares、price、10b5-1 flag、filing_time | D17/I17 | 申报事件；只保留公开市场自有资金交易 |
| U15 | 维权投资者13D催化 | filer_history、ownership_pct、purpose_text、amendments、stake_change | D18/I18 + D23/I23 | 申报事件；13D与13G分开 |
| U16 | 回购静默期供需 | authorization、actual_repurchases、cashflow_capacity、earnings_calendar、share_count | D19/I19 + D16/I16 + D15/I15 | 日历事件+季度验证 |
| U17 | 股票拆分后流动性重估 | split_ratio/date、TAQ small_trade_share、spread/depth、options_volume、valuation | D25/I25 + D02/I02 + D20/I20 | 事件+分钟/日频 |
| U18 | 分拆公司被迫抛售 | distribution_ratio、when_issued_price、parent_holders、fund_style constraints、spinoff_financials | D25/I25 + D26/I26 + D15/I15 | 分拆事件+机构截面 |
| U19 | 封闭式基金折价收敛 | NAV、market_price、distribution_coverage、leverage、corporate_actions、hedge_ETF | D40/I40 + D10/I10 + D01/I01 | 日频双标的/对冲 |
| U20 | 隔夜收益-日内反转 | previous_close、open、intraday_return、factor_expected_gap、material_news_flag | D01/I01 + D02/I02 + D23/I23 | 开盘分钟级截面 |
| U21 | 午后延续 | first_half_residual_return、relative_volume、event_tag、VWAP、market/sector_return | D02/I02 + D23/I23 + D01/I01 | 日内分钟级 |
| U22 | 波动暂停后价格发现 | LULD halt/start/end、prehalt_order_imbalance、reopen_auction、peer_return、depth | D03/I03 + D02/I02 + D01/I01 | 事件级/秒分钟级 |
| U23 | 期权隐含偏度预警 | put/call IV、25-delta skew、term_structure、spot、earnings/litigation calendar | D20/I20 + D16/I16 + D25/I25 | 日内/日频；历史期权快照 |
| U24 | 期权成交信息含量 | option trades、bid/ask、OI change、Greeks、multi_leg flags、underlying | D20/I20 | 逐笔期权；需识别组合腿和开平仓 |
| U25 | 隐含-实现波动率风险溢价 | IV surface、robust realized-vol forecast、event calendar、tail hedge price | D20/I20 + D16/I16 + D24/I24 | 日频期权组合；非单纯股票方向策略 |
| U26 | 指数成分波动率离散 | index/component option surfaces、weights、implied correlation、dividends | D20/I20 + D09/I09 + D07/I07 | 多腿期权组合；日频再平衡 |
| U27 | VIX期限结构风险开关 | VIX spot/futures curve、roll yield、credit spread、SPX exposure | D24/I24 + D20/I20 | 日频资产配置 |
| U28 | 信用-股票信号交叉 | bond/CDS spread、TRACE trades、equity return、capital_structure mapping、earnings calendar | D22/I22 + D01/I01 + D16/I16 | 双市场；债券披露延迟要建模 |
| U29 | 客户-供应商收益传导 | customer_supplier_map、revenue_exposure、customer earnings/guidance、supplier return | D11/I11 + D15/I15 + D16/I16 | 财报事件+截面 |
| U30 | 新闻情绪-价格分歧 | deduplicated_news、entity、source_quality、sentiment、market_adjusted_return | D23/I23 + D01/I01 | 新闻事件；首次发布时间和转载聚类 |
| U31 | 搜索关注冲击反转 | Google Trends/Wikipedia pageviews、retail_trade_proxy、news_flag、return | D23/I23 + D02/I02 + D01/I01 | 日/小时频；搜索数据存在抽样修订风险 |
| U32 | 空头拥挤解除 | short_interest、borrow_fee、utilization、availability、earnings/cashflow catalyst、price | D21/I21 + D16/I16 + D15/I15 | 日频+半月短仓；仅在催化和回补同时出现 |
| U33 | 税损卖出后反弹 | YTD_return、cost_basis proxy、institutional_holders、liquidity、fundamental_health | D01/I01 + D26/I26 + D15/I15 | 年末季节性截面 |
| U34 | 宏观曲线行业轮动 | yield_curve、real_yield、credit_spread、inflation/growth state、sector ETF returns | D24/I24 + D01/I01 | 日/月频资产配置 |
| U35 | 公告后并购价差 | offer_terms、deal_type、target/acquirer prices、financing、regulatory timeline、vote、borrow/options | D25/I25 + D20/I20 + D21/I21 + D01/I01 | 事件驱动多腿；协议修订需版本化 |

## 8. 加密货币策略逐项数据说明（C01-C30）

| ID | 策略 | 必需输入字段 | 数据族/来源样例 | 更新与运行形态 |
|---|---|---|---|---|
| C01 | 永续资金费率套利 | spot/perp executable prices、funding_history/next_rate、fees、borrow、balances、margin | D27/I27 + D28/I28 + D38/I38 | 多腿；秒分钟级；两端资金预置 |
| C02 | 交割合约期限基差 | spot、futures bid/ask、expiry、contract_multiplier、fees、margin、custody risk | D27/I27 + D28/I28 + D38/I38 | 多腿；分钟级到到期日 |
| C03 | 跨交易所现货价差 | synchronized L2 books、fees、balances、withdrawal status、latency、lot sizes | D27/I27 + D38/I38 | 多腿；毫秒秒级；不能假设即时转账 |
| C04 | 三角汇率套利 | 三个交易对L2、fees、min_qty、precision、balances、order latency | D27/I27 + D38/I38 | 同交易所三腿；秒级/原子或受控执行 |
| C05 | 稳定币脱锚结构化回归 | CEX/DEX price、pool depth、reserves proof、redemption status/cost、issuer news | D34/I34 + D35/I35 + D23/I23 + D38/I38 | 多场所；实时；储备风险优先于统计回归 |
| C06 | 稳定币流入风险偏好 | stablecoin supply/mint/burn、exchange netflow、market cap、BTC return | D34/I34 + D31/I31 + D27/I27 | 小时/日频资产配置 |
| C07 | 交易所净流量反转 | entity_adjusted inflow/outflow、exchange labels、internal_transfer flag、price | D31/I31 + D30/I30 + D27/I27 | 小时/日频；标签版本化 |
| C08 | 鲸鱼积累分布 | entity balances、size cohorts、exchange labels、cost basis、price | D31/I31 + D30/I30 | 日频；实体聚类版本化 |
| C09 | MVRV估值区间 | market_cap、realized_cap、MVRV、long_term_holder supply/distribution | D30/I30 | 日频周期策略 |
| C10 | SOPR投降后恢复 | entity_adjusted SOPR、spent volume、exchange inflow、price | D30/I30 + D31/I31 | 小时/日频 |
| C11 | 持币年龄带轮动 | HODL waves、coin_days_destroyed、spent_output_age、exchange destination | D30/I30 + D31/I31 | 日频 |
| C12 | 哈希带矿工投降 | hash_rate、difficulty、short/long hash averages、miner flow、price | D32/I32 + D31/I31 | 日频BTC专用 |
| C13 | 矿工储备压力 | miner reserves、miner_to_exchange flow、hash_price、energy_cost proxy、difficulty | D32/I32 + D31/I31 + D24/I24 | 日频；成本模型需注明地区假设 |
| C14 | 质押解锁供给冲击 | unlock_schedule、validator_exit_queue、staked_supply、holder_cost、liquid supply | D33/I33 + D30/I30 | 小时/日频事件 |
| C15 | 代币团队解锁做空 | team/investor unlock、labelled wallets、transfer_to_exchange、borrow fee/availability、depth | D33/I33 + D31/I31 + D38/I38 | 事件多腿/空头；借币可用性硬约束 |
| C16 | 永续持仓量清算反转 | price、OI、liquidation volume/side、funding、order-book exhaustion | D28/I28 + D27/I27 | 秒分钟级单合约 |
| C17 | 杠杆拥挤趋势破裂 | spot/perp volume share、OI change、funding、basis、price divergence | D28/I28 + D27/I27 | 分钟/小时级 |
| C18 | 期权偏度尾部防御 | 25-delta skew、IV term structure、spot beta、option liquidity | D29/I29 + D27/I27 | 日频期权/现货组合 |
| C19 | 期权到期Gamma钉住 | option OI by strike/expiry、Greeks、dealer_gamma assumption、spot、expiry clock | D29/I29 + D27/I27 | 到期日前分钟/小时；多腿/方向随gamma符号 |
| C20 | 现货成交量确认突破 | multi-exchange spot/perp volume、price、quote currency、depth、stablecoin deviation | D27/I27 + D34/I34 | 分钟/小时级单标的 |
| C21 | 横截面动量与流动性门槛 | multi-token adjusted returns、ADV/depth、spread、listing history、unlock calendar | D27/I27 + D33/I33 | 周频截面策略 |
| C22 | 小币种短期过度反转 | cross-exchange return、venue concentration、depth、news/event flag、market cap | D27/I27 + D23/I23 + D36/I36 | 分钟/小时截面；容量上限严格 |
| C23 | BTC到山寨币领先传导 | BTC/alt synchronized returns、spot volume share、rolling beta/lag、depth | D27/I27 | 分钟级配对/截面 |
| C24 | BTC主导率轮动 | BTC/ETH/alt market caps、BTC dominance、ETHBTC、breadth、liquidity | D27/I27 + D36/I36 | 日频资产配置 |
| C25 | DEX-CEX价格发现 | block/mempool swap price、pool depth、MEV flag、CEX L2、clock/latency | D35/I35 + D27/I27 | 秒/区块级多场所 |
| C26 | AMM流动性撤出预警 | pool TVL、LP add/remove、concentrated ranges、CEX depth、migration/governance event | D35/I35 + D27/I27 + D37/I37 | 区块/分钟级 |
| C27 | 协议收入质量 | fees、protocol revenue、token-holder revenue、incentive emissions、buyback/burn、token supply | D36/I36 + D33/I33 | 日/周频截面 |
| C28 | TVL增长去激励化 | TVL、net inflow、token incentives、retained active users、bridge flows、price effects | D36/I36 + D35/I35 | 日/周频截面 |
| C29 | 治理提案事件 | proposal text/type、start/end、quorum、votes/delegation、execution status、economic impact | D37/I37 + D36/I36 | 提案事件；链下Snapshot与链上执行分开 |
| C30 | 网络拥堵费率错配 | gas/fees、block utilization、active entities、L2 settlement、sequencer revenue、token return | D35/I35 + D36/I36 + D30/I30 | 区块/小时级截面 |

## 9. 怎样把外部特征真正接进 QuantDinger

当前最稳妥的实现顺序：

1. 在 `backend_api_python/app/data_providers/` 增加只读 provider，负责网络请求和原始响应标准化。
2. 在 `backend_api_python/app/services/feature_store/` 增加存储和 point-in-time 查询；不要把逻辑塞进 route 或 `backtest.py`。
3. 为特征表建立唯一键：`market + symbol + feature_name + event_time + revision_id`，重复同步保持幂等。
4. 在回测获取 OHLCV 后、执行指标前，根据回测时间窗做 `available_at` 向后连接。
5. 实盘只读取 `available_at <= now` 的最新特征，并记录数据延迟和来源。
6. 把允许注入的字段写入策略数据契约；缺字段时策略应拒绝运行，而不是默默把空值当0。

推荐接口形状：

```python
class FeatureLoader:
    def enrich(
        self,
        bars: pd.DataFrame,
        *,
        market: str,
        symbol: str,
        feature_names: list[str],
        start_time: int,
        end_time: int,
    ) -> pd.DataFrame:
        observations = self.store.query_point_in_time(
            market=market,
            symbol=symbol,
            feature_names=feature_names,
            start_time=start_time,
            end_time=end_time,
        )
        return point_in_time_join(bars, observations)
```

策略代码应显式检查字段：

```python
required = ["eps_surprise_z", "guidance_revision"]
missing = [name for name in required if name not in df.columns]
if missing:
    raise ValueError("Missing required strategy data: " + ", ".join(missing))
```

这比返回全 False 更好，因为“没有信号”和“数据根本没导入”是两件完全不同的事。

## 10. 导入质量检查清单

- 时间统一为 UTC；保留交易所本地日期作为附加字段。
- 所有公告、财报、持仓和链上标签必须有 `available_at`。
- 保存原始响应或内容哈希，能重现当时版本。
- 区分缺失值、真实0和不适用；不要一律 `fillna(0)`。
- 复权价格只用于信号计算，成交模拟保留真实历史价格和公司行动。
- 截面数据必须包含当时真实可交易的证券池，防止幸存者偏差。
- 期权、盘口和跨所数据必须保存 bid/ask 与可成交深度，不能只用中间价。
- 链上地址标签和协议分类会修订，必须保存标签版本。
- 免费接口适合原型，不等于适合生产或商业使用。
- API密钥只存在后端环境变量或密钥管理器，不写进策略代码、文档示例值或前端。

## 11. 推荐落地顺序

第一阶段先复用 D01，实现纯 OHLCV 策略和标记。第二阶段接 D04/D05/D15/D16，覆盖股票财报和事件策略。第三阶段接 D27/D28/D30/D36，覆盖加密市场与链上策略。最后才做 D02/D20/D29/D35/D38，因为逐笔、期权、DEX和多腿执行的数据量、授权和成交建模成本最高。
