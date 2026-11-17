"""Dashboard entry point. Run with:  streamlit run app/main.py

Sets up the page, draws the trade selector in the sidebar (shared by every
page) and hands over to whichever page is selected.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "app"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import streamlit as st


def _refresh_code_if_updated() -> None:
    """Drop the loaded engine code if the files on disk are newer.

    When new code is uploaded, the hosting service updates the files but keeps
    the app running, so the calculation code already in memory would be the old
    version while the pages are the new one. Comparing the newest file time on
    each run and forgetting the old copy keeps the two in step. Cached price
    data and chart results are cleared too, since they were built by old code.
    """
    watched = [*(ROOT / "engine").glob("*.py"), *(ROOT / "data" / "assumptions").glob("*.yaml"),
               ROOT / "app" / "ui.py", ROOT / "app" / "charts.py"]
    newest = max(path.stat().st_mtime for path in watched)
    if getattr(sys, "_arb_engine_code_time", None) != newest:
        for name in [m for m in sys.modules if m in ("ui", "charts", "engine") or m.startswith("engine.")]:
            del sys.modules[name]
        st.cache_data.clear()
    sys._arb_engine_code_time = newest


_refresh_code_if_updated()

import ui

st.set_page_config(page_title="Crude Arbitrage & Voyage Engine", page_icon=":material/sailing:",
                   layout="wide")

# One file per page. A page appears in the menu once its file exists.
PAGES = [
    ("home.py", "Start here", ":material/home:"),
    ("voyage_page.py", "Voyage calculator", ":material/sailing:"),
    ("prices_page.py", "Prices", ":material/show_chart:"),
    ("arbitrage_page.py", "Arbitrage result", ":material/paid:"),
    ("ranking_page.py", "Where to send it", ":material/leaderboard:"),
    ("scenarios_page.py", "Scenarios & history", ":material/tune:"),
    ("methodology_page.py", "Methodology", ":material/menu_book:"),
]
app_dir = Path(__file__).parent
pages = [st.Page(app_dir / file, title=title, icon=icon, default=(file == "home.py"))
         for file, title, icon in PAGES if (app_dir / file).exists()]
current_page = st.navigation(pages)

st.session_state["setup"] = ui.sidebar_setup()
st.sidebar.divider()
st.sidebar.caption("Uses public benchmark prices and documented estimates. It does not use real "
                   "traded freight or physical premium data, and it does not forecast.")
current_page.run()
