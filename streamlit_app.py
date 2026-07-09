from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).parent


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def build_component_html() -> str:
    html = read_text("index.html")
    css = read_text("styles.css")
    js = read_text("app.js")

    html = html.replace('<link rel="stylesheet" href="./styles.css">', f"<style>{css}</style>")
    html = html.replace('<script src="./app.js"></script>', f"<script>{js}</script>")
    return html


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
