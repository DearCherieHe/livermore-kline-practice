# Remote Execution Handoff

This is the single living prompt for the remote high-permission Codex environment.

Rule: do not create separate handoff prompts. Update this file in place, and keep the newest required action at the top under "Current Task".

## Current Task

Status: latest

### Context

This repository contains a Streamlit app called `livermore-kline-practice`.

The app lets the user manually record OHLCV rows, draw K-lines/candlesticks, and replay history through a timeline. Most code and design work is done in a restricted environment. The remote environment is only needed for dependency installation, live data download, and runtime verification.

Repo-visible data and scripts:

```text
data/
scripts/
```

Already completed:

- A small deployable bundled sample was copied into:

```text
data/
```

- `data/manifest.json` currently indexes the bundled sample datasets.
- The Streamlit app now supports:
  - manual OHLCV entry
  - CSV/JSON import
  - bundled sample dataset dropdown
  - timeline replay

### Why Remote Execution Is Needed

The restricted environment cannot install packages or make outbound download requests.

The remote environment should run dependency installation, live market-data download, and verification.

### Please Do This In The Remote Environment

1. Open the repository root.

2. Install dependencies:

```bash
python3 -m pip install -r requirements_data.txt
```

3. Run the downloader:

```bash
python3 scripts/download_market_data.py
```

Expected behavior:

- downloads US and HK sample daily data through `yfinance`
- downloads A-share sample daily data through `baostock`
- writes raw files under:

```text
downloaded_raw/
```

- writes website-ready files under:

```text
data/downloaded/
```

- updates:

```text
data/manifest.json
```

4. Keep the deployable subset modest so GitHub/Streamlit deployment stays light.

- US: AAPL, MSFT, NVDA, AMZN, TSLA, META, GOOGL
- HK: 0700.HK, 9988.HK, 3690.HK, 2800.HK
- A-share: sh.600519, sz.300750, sh.600036, sh.601318

5. Verify:

```bash
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('streamlit_app.py').read_text()); print('streamlit syntax ok')"
node --check app.js
```

If Streamlit is available, also run:

```bash
streamlit run streamlit_app.py
```

Then verify the app loads and the bundled dataset dropdown can load at least one US, HK, and A-share dataset.

### Report Back

Please report:

- whether dependency installation succeeded
- whether yfinance US/HK downloads succeeded
- whether baostock A-share downloads succeeded
- how many datasets are in `data/manifest.json`
- which datasets were added under `data/`
- any error messages, especially network, package, or API failures

## Handoff Log

### 2026-07-10

Initial repo-tracked handoff created for installing market-data dependencies and running `scripts/download_market_data.py` in the remote environment.
