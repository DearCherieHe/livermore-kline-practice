#!/usr/bin/env python3
"""Download US, HK, and A-share OHLCV data for bundled app samples."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "downloaded_raw"
DATA = ROOT / "data"
READY = DATA / "downloaded"

US_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "META", "GOOGL"]
HK_TICKERS = ["0700.HK", "9988.HK", "3690.HK", "2800.HK"]
A_SHARE_CODES = [
    ("sh.600519", "Kweichow Moutai"),
    ("sz.300750", "CATL"),
    ("sh.600036", "China Merchants Bank"),
    ("sh.601318", "Ping An Insurance"),
]


def csv_name(symbol: str) -> str:
    return symbol.replace(".", "_").replace("-", "_")


def write_ready_csv(path: Path, rows: list[dict[str, str]]) -> dict[str, str | int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [row for row in rows if all(row.get(k) for k in ["time", "open", "high", "low", "close", "volume"])]
    rows.sort(key=lambda row: row["time"])

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "open", "high", "low", "close", "volume", "note"])
        writer.writeheader()
        writer.writerows(rows)

    return {
        "rows": len(rows),
        "start": rows[0]["time"] if rows else "",
        "end": rows[-1]["time"] if rows else "",
    }


def read_manifest() -> dict:
    path = DATA / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": "livermore-kline-practice-v1",
        "columns": ["time", "open", "high", "low", "close", "volume", "note"],
        "datasets": [],
    }


def update_manifest(items: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    datasets = manifest.get("datasets", [])
    incoming = {(item["source"], item["symbol"]) for item in items}
    datasets = [item for item in datasets if (item.get("source"), item.get("symbol")) not in incoming]
    datasets.extend(items)
    datasets.sort(key=lambda item: (item.get("market", ""), item.get("symbol", ""), item.get("source", "")))
    manifest["datasets"] = datasets
    manifest["count"] = len(datasets)
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def download_yfinance() -> list[dict]:
    import yfinance as yf

    manifest = []
    for market, tickers in [("US", US_TICKERS), ("HK", HK_TICKERS)]:
        for ticker in tickers:
            data = yf.download(ticker, start="2010-01-01", auto_adjust=False, progress=False)
            if data.empty:
                print(f"skip empty {ticker}")
                continue

            raw_path = RAW / market.lower() / f"{csv_name(ticker)}.csv"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            data.to_csv(raw_path)

            rows = []
            for idx, row in data.iterrows():
                rows.append(
                    {
                        "time": idx.strftime("%Y-%m-%d"),
                        "open": str(row["Open"]),
                        "high": str(row["High"]),
                        "low": str(row["Low"]),
                        "close": str(row["Close"]),
                        "volume": str(int(row["Volume"])),
                        "note": f"{ticker} | yfinance | raw OHLC, not adjusted",
                    }
                )

            ready_path = READY / market.lower() / f"{csv_name(ticker)}.csv"
            stats = write_ready_csv(ready_path, rows)
            manifest.append(
                {
                    "symbol": ticker,
                    "name": ticker,
                    "market": market,
                    "source": "yfinance",
                    "file": str(ready_path.relative_to(DATA)),
                    **stats,
                }
            )
    return manifest


def download_baostock() -> list[dict]:
    import baostock as bs

    fields = "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
    manifest = []
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"baostock login failed: {login.error_msg}")

    try:
        for code, name in A_SHARE_CODES:
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date="2010-01-01",
                frequency="d",
                adjustflag="3",
            )
            raw_rows = []
            while rs.next():
                raw_rows.append(dict(zip(rs.fields, rs.get_row_data())))

            raw_path = RAW / "a_share" / f"{csv_name(code)}.csv"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with raw_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rs.fields)
                writer.writeheader()
                writer.writerows(raw_rows)

            rows = [
                {
                    "time": row["date"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                    "note": f"{code} | {name} | baostock | adjustflag=3 raw",
                }
                for row in raw_rows
                if row.get("tradestatus") == "1"
            ]

            ready_path = READY / "a_share" / f"{csv_name(code)}.csv"
            stats = write_ready_csv(ready_path, rows)
            manifest.append(
                {
                    "symbol": code,
                    "name": name,
                    "market": "A-share",
                    "source": "baostock",
                    "file": str(ready_path.relative_to(DATA)),
                    **stats,
                }
            )
    finally:
        bs.logout()
    return manifest


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    READY.mkdir(parents=True, exist_ok=True)
    items = []
    items.extend(download_yfinance())
    items.extend(download_baostock())
    update_manifest(items)
    print(f"Downloaded and normalized {len(items)} datasets.")
    print(f"Raw files: {RAW}")
    print(f"Website-ready files: {READY}")


if __name__ == "__main__":
    main()
