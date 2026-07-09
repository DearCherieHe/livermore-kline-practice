# Livermore Tape Ledger

一个本地静态网页，用来练习手动记录行情并绘制 K 线。

## 设计思路

- 先写下每根 K 线的时间、开盘、最高、最低、收盘和成交量。
- 点击“落笔绘制”后，这根数据才进入画布。
- 时间线滑块只显示截至某一刻的历史，用来复盘当时能看到的信息。
- 数据保存在浏览器 localStorage，可导出和导入 JSON。

## 使用

直接打开 `index.html`。

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
- `streamlit_app.py`：Streamlit 部署入口
- `requirements.txt`：Streamlit 依赖
