#!/usr/bin/env python3
"""Download US, HK, and A-share OHLCV data for bundled app samples."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "downloaded_raw"
DATA = ROOT / "data"
READY = DATA / "downloaded"

US_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "TSLA",
    "AVGO",
    "ORCL",
    "AMD",
    "INTC",
    "QCOM",
    "MU",
    "TXN",
    "ADI",
    "AMAT",
    "LRCX",
    "KLAC",
    "CRM",
    "NOW",
    "ADBE",
    "INTU",
    "SHOP",
    "SNOW",
    "PLTR",
    "PANW",
    "CRWD",
    "DDOG",
    "NET",
    "MDB",
    "UBER",
    "ABNB",
    "COIN",
    "PYPL",
    "XYZ",
    "NFLX",
    "DIS",
    "IBM",
    "CSCO",
    "ACN",
    "ANET",
    "ARM",
    "ASML",
    "TSM",
    "MRVL",
    "MCHP",
    "NXPI",
    "ON",
    "MPWR",
    "TEAM",
    "WDAY",
    "ZS",
    "OKTA",
    "HUBS",
    "ROKU",
    "APP",
    "RBLX",
    "TTD",
    "BIDU",
    "BABA",
    "JD",
    "PDD",
    "LI",
    "NIO",
    "XPEV",
]
HK_TICKERS = ["0700.HK", "9988.HK", "3690.HK", "2800.HK"]
A_SHARE_CODES = [
    ("sh.600519", "贵州茅台"),
    ("sz.300750", "宁德时代"),
    ("sh.600036", "招商银行"),
    ("sh.601318", "中国平安"),
]
A_SHARE_FOCUS_CODES = [
    "sh.600089",
    "sh.600438",
    "sh.600460",
    "sh.600570",
    "sh.600584",
    "sh.600588",
    "sh.600703",
    "sh.600745",
    "sh.601012",
    "sh.601138",
    "sh.601360",
    "sh.603019",
    "sh.603259",
    "sh.603501",
    "sh.603986",
    "sh.605358",
    "sh.688008",
    "sh.688009",
    "sh.688012",
    "sh.688036",
    "sh.688041",
    "sh.688111",
    "sh.688126",
    "sh.688169",
    "sh.688187",
    "sh.688223",
    "sh.688256",
    "sh.688271",
    "sh.688303",
    "sh.688396",
    "sh.688475",
    "sh.688599",
    "sh.688981",
    "sz.000063",
    "sz.000100",
    "sz.000725",
    "sz.000938",
    "sz.002049",
    "sz.002129",
    "sz.002179",
    "sz.002230",
    "sz.002236",
    "sz.002241",
    "sz.002371",
    "sz.002415",
    "sz.002459",
    "sz.002460",
    "sz.002475",
    "sz.002594",
    "sz.002812",
    "sz.002938",
    "sz.300001",
    "sz.300003",
    "sz.300014",
    "sz.300015",
    "sz.300033",
    "sz.300059",
    "sz.300122",
    "sz.300124",
    "sz.300274",
    "sz.300308",
    "sz.300316",
    "sz.300347",
    "sz.300394",
    "sz.300408",
    "sz.300413",
    "sz.300433",
    "sz.300442",
    "sz.300450",
    "sz.300454",
    "sz.300496",
    "sz.300502",
    "sz.300628",
    "sz.300661",
    "sz.300750",
    "sz.300751",
    "sz.300759",
    "sz.300760",
    "sz.300763",
    "sz.300769",
    "sz.300782",
    "sz.300896",
    "sz.300999",
    "sz.301236",
    "sz.301269",
    "sz.301308",
]
A_SHARE_STOCK_PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30", "bj.")


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


def download_yfinance(start_date: str, markets: set[str]) -> list[dict]:
    import yfinance as yf

    manifest = []
    for market, tickers in [("US", US_TICKERS), ("HK", HK_TICKERS)]:
        if market.lower() not in markets:
            continue
        for ticker in tickers:
            data = yf.download(ticker, start=start_date, auto_adjust=False, progress=False)
            if data.empty:
                print(f"skip empty {ticker}")
                continue
            if hasattr(data.columns, "nlevels") and data.columns.nlevels > 1:
                data = data.xs(ticker, axis=1, level="Ticker")

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


def latest_trade_date(bs) -> str:
    today = date.today()
    start = today - timedelta(days=14)
    rs = bs.query_trade_dates(start_date=start.isoformat(), end_date=today.isoformat())
    if rs.error_code != "0":
        raise RuntimeError(f"baostock query_trade_dates failed: {rs.error_msg}")

    dates = []
    while rs.next():
        row = dict(zip(rs.fields, rs.get_row_data()))
        if row.get("is_trading_day") == "1":
            dates.append(row["calendar_date"])
    if not dates:
        raise RuntimeError("baostock returned no recent trading days")
    return dates[-1]


def get_a_share_name_map(bs, universe_date: str | None) -> dict[str, str]:
    universe_date = universe_date or latest_trade_date(bs)
    rs = bs.query_all_stock(day=universe_date)
    if rs.error_code != "0":
        raise RuntimeError(f"baostock query_all_stock failed: {rs.error_msg}")

    names = {}
    while rs.next():
        row = dict(zip(rs.fields, rs.get_row_data()))
        code = row.get("code", "")
        if row.get("tradeStatus") == "1" and code:
            names[code] = row.get("code_name", code)
    return names


def get_a_share_codes(bs, universe: str, universe_date: str | None) -> list[tuple[str, str]]:
    if universe == "sample":
        return A_SHARE_CODES
    if universe == "focus":
        names = get_a_share_name_map(bs, universe_date)
        return [(code, names.get(code, code)) for code in A_SHARE_FOCUS_CODES]

    universe_date = universe_date or latest_trade_date(bs)
    print(f"Using A-share universe date: {universe_date}")
    codes = []
    rs = bs.query_all_stock(day=universe_date)
    if rs.error_code != "0":
        raise RuntimeError(f"baostock query_all_stock failed: {rs.error_msg}")

    while rs.next():
        row = dict(zip(rs.fields, rs.get_row_data()))
        code = row.get("code", "")
        if row.get("tradeStatus") == "1" and code.startswith(A_SHARE_STOCK_PREFIXES):
            codes.append((code, row.get("code_name", code)))

    codes.sort(key=lambda item: item[0])
    return codes


def download_baostock(
    start_date: str,
    universe: str,
    markets: set[str],
    limit: int | None,
    universe_date: str | None,
) -> list[dict]:
    import baostock as bs

    if "a-share" not in markets:
        return []

    fields = "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
    manifest = []
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"baostock login failed: {login.error_msg}")

    try:
        codes = get_a_share_codes(bs, universe, universe_date)
        if limit is not None:
            codes = codes[:limit]
        for index, (code, name) in enumerate(codes, start=1):
            print(f"[A-share {index}/{len(codes)}] {code} {name}")
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=start_date,
                frequency="d",
                adjustflag="3",
            )
            if rs.error_code != "0":
                print(f"skip {code}: {rs.error_msg}")
                continue
            raw_rows = []
            while rs.next():
                raw_rows.append(dict(zip(rs.fields, rs.get_row_data())))
            if not raw_rows:
                print(f"skip empty {code}")
                continue

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


def parse_markets(value: str) -> set[str]:
    markets = {item.strip().lower() for item in value.split(",") if item.strip()}
    valid = {"us", "hk", "a-share"}
    unknown = markets - valid
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown market(s): {', '.join(sorted(unknown))}")
    return markets


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and normalize OHLCV datasets.")
    parser.add_argument(
        "--universe",
        choices=["sample", "focus", "full-a-share"],
        default="sample",
        help="sample keeps a tiny set; focus adds major China tech/ChiNext/STAR stocks; full-a-share traverses every active A-share stock returned by baostock.",
    )
    parser.add_argument("--markets", type=parse_markets, default=parse_markets("us,hk,a-share"))
    parser.add_argument("--start-date", default="2010-01-01")
    parser.add_argument("--universe-date", default=None, help="trading date used to enumerate the full A-share universe")
    parser.add_argument("--limit", type=int, default=None, help="optional cap for smoke-testing large universes")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    READY.mkdir(parents=True, exist_ok=True)
    items = []
    items.extend(download_yfinance(args.start_date, args.markets))
    items.extend(
        download_baostock(
            args.start_date,
            args.universe,
            args.markets,
            args.limit,
            args.universe_date,
        )
    )
    update_manifest(items)
    print(f"Downloaded and normalized {len(items)} datasets.")
    print(f"Raw files: {RAW}")
    print(f"Website-ready files: {READY}")


if __name__ == "__main__":
    main()
