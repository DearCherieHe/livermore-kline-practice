# Cherie Handoff

This is the single living prompt for the Cherie Codex account.

Rule for Serena/Codex: do not create separate handoff prompts. Update this file in place, and keep the newest required action at the top under "Current Task".

## Current Task

Status: latest

### Context

Serena is building a Streamlit app called `livermore-kline-practice`.

The app lets the user manually record OHLCV rows, draw K-lines/candlesticks, and replay history through a timeline. Most code and design work is done on the low-permission Serena machine.

Repository:

```text
/Users/serena/Documents/Notes/Trade/Github/livermore-kline-practice
```

Local stock data workspace:

```text
/Users/serena/Documents/Notes/Trade/stockdata
```

Already completed on Serena:

- Existing downloaded stock files were normalized into:

```text
/Users/serena/Documents/Notes/Trade/stockdata/website_ready
```

- `website_ready/manifest.json` contains 8628 normalized datasets.
- A small deployable bundled sample was copied into the Streamlit repo:

```text
/Users/serena/Documents/Notes/Trade/Github/livermore-kline-practice/data
```

- The Streamlit app now supports:
  - manual OHLCV entry
  - CSV/JSON import
  - bundled sample dataset dropdown
  - timeline replay

### Why Cherie Is Needed

The Serena machine cannot install packages or make outbound download requests because of restricted network/admin permissions.

Cherie should run the dependency installation and live market-data download/verification.

### Please Do This On Cherie

1. Open this folder:

```text
/Users/serena/Documents/Notes/Trade/stockdata
```

2. Install dependencies locally into `.vendor`:

```bash
python3 -m pip install --target .vendor -r requirements_data.txt
```

3. Run the downloader:

```bash
python3 download_market_data.py
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
website_ready/downloaded/
```

- updates:

```text
website_ready/manifest.json
```

4. If the download succeeds, copy a small deployable subset into:

```text
/Users/serena/Documents/Notes/Trade/Github/livermore-kline-practice/data
```

Recommended deployable subset:

- US: AAPL, MSFT, NVDA, AMZN, TSLA, META, GOOGL
- HK: 0700.HK, 9988.HK, 3690.HK, 2800.HK
- A-share: sh.600519, sz.300750, sh.600036, sh.601318

Keep this subset modest so GitHub/Streamlit deployment stays light.

5. Rebuild or update:

```text
/Users/serena/Documents/Notes/Trade/Github/livermore-kline-practice/data/manifest.json
```

6. Verify:

```bash
cd /Users/serena/Documents/Notes/Trade/Github/livermore-kline-practice
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('streamlit_app.py').read_text()); print('streamlit syntax ok')"
node --check app.js
```

If Streamlit is installed on Cherie, also run:

```bash
streamlit run streamlit_app.py
```

Then verify the app loads and the bundled dataset dropdown can load at least one US, HK, and A-share dataset.

### Report Back

Please report:

- whether dependency installation succeeded
- whether yfinance US/HK downloads succeeded
- whether baostock A-share downloads succeeded
- how many datasets are in `website_ready/manifest.json`
- which datasets were copied into the Streamlit repo `data/`
- any error messages, especially network, package, or API failures

## Handoff Log

### 2026-07-10

Initial repo-tracked handoff created for installing market-data dependencies and running `download_market_data.py` on Cherie.
