# Livermore Tape Ledger

一个本地静态网页，用来练习手动记录行情并绘制 K 线。

## 设计思路

- 先写下每根 K 线的时间、开盘、最高、最低、收盘和成交量。
- 点击“落笔绘制”后，这根数据才进入画布。
- 时间线滑块只显示截至某一刻的历史，用来复盘当时能看到的信息。
- 数据保存在浏览器 localStorage，可导出 JSON，也可导入 JSON/CSV。

## 使用

直接打开 `index.html`。

在 Streamlit 版本里，可以直接用顶部的“内置数据”下拉框载入样本行情；也可以用“导入数据”上传自己的 CSV/JSON。

## 导入数据格式

支持本工具导出的 JSON，也支持 CSV。

CSV 推荐表头：

```csv
time,open,high,low,close,volume,note
2026-07-10 09:30,100,102,99,101,8200,第一根
2026-07-10 10:30,101,104,100,103,11200,突破前高
```

字段也兼容 `date/timestamp`、`o/h/l/c`、`vol/v` 这类常见写法。

仓库里有一个 `sample_import.csv`，可以先用它测试导入。

## 内置数据

`data/` 目录包含一小批适合部署的样本：

- US: AAPL, AMZN, GOOGL, IBM, MSFT, NVDA, TSLA
- US ETF: SPY, QQQ

这些样本主要用于练习 K 线记录和时间线复盘，不代表无幸存者偏差的严肃回测数据。全量研究数据不放在这个部署仓库里。

## 下载新样本数据

需要联网环境：

```bash
python3 -m pip install -r requirements_data.txt
python3 scripts/download_market_data.py
```

脚本会把网站可用文件写到 `data/downloaded/`，并更新 `data/manifest.json`。

## Streamlit 部署

这个目录也可以作为 Streamlit app 部署。

本地运行：

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Streamlit Cloud：

1. 把 `livermore-kline-practice` 上传到 GitHub 仓库。
2. 在 Streamlit Cloud 选择该仓库。
3. Main file path 填 `streamlit_app.py`。

## 文件

- `index.html`：页面结构
- `styles.css`：界面样式
- `app.js`：录入、绘图、时间线和本地存储逻辑
- `sample_import.csv`：CSV 导入示例
- `data/`：Streamlit 内置样本数据
- `streamlit_app.py`：Streamlit 部署入口
- `requirements.txt`：Streamlit 依赖
