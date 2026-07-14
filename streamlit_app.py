from pathlib import Path
import csv
import json

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).parent


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def build_component_html(bundled: list[dict]) -> str:
    html = read_text("index.html")
    css = read_text("styles.css")
    js = read_text("app.js")

    html = html.replace('<link rel="stylesheet" href="./styles.css">', f"<style>{css}</style>")
    html = html.replace(
        '<script src="./app.js"></script>',
        f"<script>window.BUNDLED_DATASETS = {json.dumps(bundled, ensure_ascii=False)};</script><script>{js}</script>",
    )
    return html


def read_manifest_items() -> list[dict]:
    manifest_path = ROOT / "data" / "manifest.json"
    if not manifest_path.exists():
        return []

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [item for item in manifest.get("datasets", []) if (ROOT / "data" / item.get("file", "")).exists()]


def read_bundled_dataset(item: dict) -> dict:
    data_path = ROOT / "data" / item["file"]
    with data_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        "symbol": item.get("symbol", data_path.stem),
        "name": item.get("name", data_path.stem),
        "market": item.get("market", ""),
        "source": item.get("source", ""),
        "rows": rows,
    }


def dataset_label(item: dict) -> str:
    return " · ".join(
        str(part)
        for part in [
            item.get("symbol"),
            item.get("name"),
            item.get("market"),
            f"{item.get('rows', 0)} 根",
        ]
        if part
    )


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
      [data-testid="stSelectbox"] {
        padding: 10px 16px 0;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

manifest_items = read_manifest_items()
selected_item = st.selectbox(
    "内置数据",
    manifest_items,
    format_func=dataset_label,
    label_visibility="collapsed",
) if manifest_items else None
bundled = [read_bundled_dataset(selected_item)] if selected_item else []

components.html(build_component_html(bundled), height=980, scrolling=True)
