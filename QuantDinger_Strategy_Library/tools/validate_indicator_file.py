"""Validate a standalone QuantDinger IndicatorStrategy without starting the web app."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


FOUR_WAY = ("open_long", "close_long", "open_short", "close_short")


def sample_df(length: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0002, 0.018, length)
    close = 100 * np.exp(np.cumsum(returns))
    open_price = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.003, length))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0, 0.012, length))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0, 0.012, length))
    volume = rng.lognormal(12, 0.55, length)
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=length, freq="D"),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def parse_params(code: str) -> dict[str, object]:
    values: dict[str, object] = {}
    pattern = re.compile(
        r"^\s*#\s*@param\s+(\w+)\s+(int|float|bool|str|string)\s+(\S+)",
        re.MULTILINE | re.IGNORECASE,
    )
    for name, kind, raw in pattern.findall(code):
        if kind == "int":
            values[name] = int(raw)
        elif kind == "float":
            values[name] = float(raw)
        elif kind == "bool":
            values[name] = raw.lower() == "true"
        else:
            values[name] = raw
    return values


def validate(path: Path) -> list[str]:
    code = path.read_text(encoding="utf-8")
    problems: list[str] = []
    if re.search(r"\.shift\(\s*-\d+", code):
        problems.append("future-looking negative shift found")

    df = sample_df()
    env = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "params": parse_params(code),
        "output": None,
    }
    for column in ("open", "high", "low", "close", "volume"):
        env[column] = env["df"][column]
    exec(compile(code, str(path), "exec"), env, env)

    executed_df = env["df"]
    for column in FOUR_WAY:
        if column not in executed_df:
            problems.append(f"missing execution column: {column}")
            continue
        if len(executed_df[column]) != len(df):
            problems.append(f"execution column length mismatch: {column}")
        if executed_df[column].fillna(False).astype(bool).dtype != bool:
            problems.append(f"execution column is not boolean: {column}")

    output = env.get("output")
    if not isinstance(output, dict):
        problems.append("output must be a dict")
        return problems

    for group in ("plots", "signals"):
        values = output.get(group)
        if not isinstance(values, list):
            problems.append(f"output[{group!r}] must be a list")
            continue
        for index, item in enumerate(values):
            data = item.get("data") if isinstance(item, dict) else None
            if not isinstance(data, list) or len(data) != len(df):
                problems.append(f"{group}[{index}] data length mismatch")
                continue
            if group == "signals":
                invalid = [
                    value
                    for value in data
                    if value is not None
                    and (not isinstance(value, (int, float)) or not math.isfinite(float(value)))
                ]
                if invalid:
                    problems.append(f"signals[{index}] contains invalid marker values")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        try:
            problems = validate(path)
        except Exception as exc:
            problems = [f"execution failed: {type(exc).__name__}: {exc}"]
        if problems:
            failed = True
            print(f"FAIL {path}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
