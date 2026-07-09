from pathlib import Path
import csv
import json

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).parent


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def build_component_html() -> str:
    html = read_text("index.html")
    css = read_text("styles.css")
    js = read_text("app.js")
    bundled = read_bundled_datasets()

    html = html.replace('<link rel="stylesheet" href="./styles.css">', f"<style>{css}</style>")
    html = html.replace(
        '<script src="./app.js"></script>',
        f"<script>window.BUNDLED_DATASETS = {json.dumps(bundled, ensure_ascii=False)};</script><script>{js}</script>",
    )
    return html


def read_bundled_datasets() -> list[dict]:
    manifest_path = ROOT / "data" / "manifest.json"
    if not manifest_path.exists():
        return []

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = []
    for item in manifest.get("datasets", []):
        data_path = ROOT / "data" / item["file"]
        if not data_path.exists():
            continue
        with data_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        datasets.append(
            {
                "symbol": item.get("symbol", data_path.stem),
                "name": item.get("name", data_path.stem),
                "market": item.get("market", ""),
                "source": item.get("source", ""),
                "rows": rows,
            }
        )
    return datasets


st.set_page_config(
    page_title="Livermore Tape Ledger",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container {
        padding: 0;
        max-width: none;
      }
      header[data-testid="stHeader"],
      footer {
        display: none;
      }
      iframe {
        display: block;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(build_component_html(), height=980, scrolling=True)
