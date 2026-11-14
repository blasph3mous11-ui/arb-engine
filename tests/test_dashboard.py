"""Smoke test: every dashboard page loads without an error, for several trade set-ups.

Uses Streamlit's built-in test runner, so no browser is needed. Prices come
from the snapshot shipped with the project, so the test works offline.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from engine import prices

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py", "voyage_page.py", "prices_page.py", "arbitrage_page.py",
         "scenarios_page.py", "methodology_page.py"]
SETUPS = [
    {},                                                    # the starting case
    {"vessel": "vlcc"},                                    # too deep for Suez: forced via the Cape
    {"vessel": "aframax", "via": "cape", "market": "calm_2024"},
    {"benchmark": "dubai", "destination": "mumbai", "origin": "houston"},
]


@pytest.fixture(autouse=True)
def offline_prices(monkeypatch):
    seed = prices._read(prices.SEED_FILE)
    monkeypatch.setattr(prices, "load_benchmarks", lambda refresh=False: (seed, "Test snapshot."))


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("setup", SETUPS, ids=["base", "vlcc", "aframax-cape-calm", "dubai-mumbai"])
def test_page_loads(page, setup):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    for key, value in setup.items():
        widget = app.radio(key=key) if key == "via" else app.selectbox(key=key)
        widget.set_value(value)
    app.run()
    app.switch_page(str(ROOT / "app" / page)).run()
    assert not app.exception, f"{page} raised: {[e.value for e in app.exception]}"
    assert len(app.title) == 1
