"""Benchmark crude prices from free public sources, cached on disk.

Sources (no sign-up or key needed):
  * Brent and WTI daily spot prices: US Energy Information Administration (EIA).
  * Dubai monthly average: World Bank commodity "Pink Sheet". No free daily
    Dubai price exists, so Dubai is monthly only.

Downloads are saved under data/cache/ so the dashboard works offline and does
not hammer the sources. If a download fails we fall back to the last cache,
and if there is no cache at all, to a small snapshot shipped with the project.
"""

import io
import re
import time
from pathlib import Path

import pandas as pd
import requests

from engine import assumptions as A

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache"
SEED_FILE = ROOT / "data" / "seed" / "benchmarks_seed.csv"
CACHE_FILE = CACHE_DIR / "benchmarks.csv"

EIA_URL = "https://www.eia.gov/dnav/pet/hist_xls/{code}d.xls"
EIA_SERIES = {"brent": "RBRTE", "wti": "RWTC"}
# The World Bank moves its monthly price file to a new address each year, so we
# read the current link off its commodity-markets page and keep a known one as back-up.
WORLD_BANK_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
WORLD_BANK_LINK = r'https://thedocs\.worldbank\.org[^"]*CMO-Historical-Data-Monthly\.xlsx'
WORLD_BANK_URL = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
                  "related/CMO-Historical-Data-Monthly.xlsx")
SOURCES = {
    "brent": "US EIA, Europe Brent Spot Price FOB (daily)",
    "wti": "US EIA, Cushing OK WTI Spot Price FOB (daily)",
    "dubai": "World Bank Pink Sheet, Crude oil Dubai (monthly average)",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (educational crude-arbitrage dashboard)"}
MAX_CACHE_AGE_HOURS = 24


def _download(url: str) -> bytes:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.content


def parse_eia_xls(content: bytes) -> pd.Series:
    """EIA history files hold the data on sheet 'Data 1': date, price."""
    sheet = pd.read_excel(io.BytesIO(content), sheet_name="Data 1", skiprows=2)
    sheet.columns = ["date", "price"]
    sheet = sheet.dropna()
    return pd.Series(sheet["price"].astype(float).values,
                     index=pd.to_datetime(sheet["date"]).dt.normalize())


def parse_world_bank_dubai(content: bytes) -> pd.Series:
    """Pick the 'Crude oil, Dubai' column out of the Pink Sheet monthly table."""
    sheet = pd.read_excel(io.BytesIO(content), sheet_name="Monthly Prices", header=None)
    header_row = next(i for i in range(15)
                      if sheet.iloc[i].astype(str).str.contains("Crude oil, Dubai").any())
    column = next(c for c in sheet.columns if "Crude oil, Dubai" in str(sheet.iloc[header_row, c]))
    months, values = [], []
    for label, value in zip(sheet[0], sheet[column]):
        match = re.fullmatch(r"(\d{4})M(\d{2})", str(label))  # e.g. 2026M09
        if match and pd.notna(pd.to_numeric(value, errors="coerce")):
            months.append(pd.Timestamp(int(match[1]), int(match[2]), 1))
            values.append(float(value))
    return pd.Series(values, index=months)


def world_bank_url() -> str:
    """Address of the current World Bank monthly price file."""
    try:
        match = re.search(WORLD_BANK_LINK, _download(WORLD_BANK_PAGE).decode("utf-8", "ignore"))
        return match[0] if match else WORLD_BANK_URL
    except Exception:
        return WORLD_BANK_URL


def download_benchmarks() -> pd.DataFrame:
    """Fetch everything and combine into one daily table: brent, wti, dubai."""
    table = pd.DataFrame({name: parse_eia_xls(_download(EIA_URL.format(code=code)))
                          for name, code in EIA_SERIES.items()})
    try:
        dubai = parse_world_bank_dubai(_download(world_bank_url()))
        # Spread each monthly average across the days of that month.
        month_start = table.index.to_period("M").to_timestamp()
        table["dubai"] = dubai.reindex(month_start).values
    except Exception:
        table["dubai"] = float("nan")  # Dubai is optional; Brent and WTI are enough
    table.index.name = "date"
    return table


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"], index_col="date")


def _download_time_note() -> str:
    """When the saved price file was last written, so the claim can be checked."""
    saved_at = pd.Timestamp(CACHE_FILE.stat().st_mtime, unit="s", tz="UTC")
    return f"Prices last downloaded from EIA / World Bank on {saved_at:%d %b %Y at %H:%M} UTC."


def load_benchmarks(refresh: bool = False) -> tuple[pd.DataFrame, str]:
    """Daily benchmark prices in USD per barrel, and a note on where they came from."""
    cache_is_fresh = (CACHE_FILE.exists()
                      and time.time() - CACHE_FILE.stat().st_mtime < MAX_CACHE_AGE_HOURS * 3600)
    if cache_is_fresh and not refresh:
        return _read(CACHE_FILE), _download_time_note()
    try:
        table = download_benchmarks()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        table.to_csv(CACHE_FILE)
        return table, _download_time_note()
    except Exception as error:
        if CACHE_FILE.exists():
            return _read(CACHE_FILE), (f"Download failed ({type(error).__name__}); showing the saved copy. "
                                       + _download_time_note())
        return _read(SEED_FILE), ("Download failed and no saved copy exists; showing the snapshot "
                                  "shipped with the project, which may be out of date.")


def latest(prices: pd.DataFrame, column: str) -> tuple[float, pd.Timestamp]:
    """Most recent available price in a column, and its date."""
    series = prices[column].dropna()
    return float(series.iloc[-1]), series.index[-1]


def monthly_averages(prices: pd.DataFrame, destination_column: str = "dubai",
                     origin_column: str = "wti") -> pd.DataFrame:
    """One row per calendar month: the average of each price over that month.

    Dubai is only published as a monthly average. Setting it against a single
    day's WTI would mix a month with a day and invent price gaps that never
    existed, so for Dubai we compare month with month. Months with no WTI or
    no destination price are dropped. Rows are dated the first of the month.
    """
    monthly = prices.resample("MS").mean()
    return monthly.dropna(subset=[origin_column, destination_column])


def bunker_price_estimate(brent_usd_per_bbl: float) -> float:
    """Estimated ship-fuel price in USD per tonne, from the Brent price.

    This is an ESTIMATE: real bunker prices are published by paid services.
    The ratio and its reasoning are in data/assumptions/market.yaml.
    """
    return brent_usd_per_bbl * A.get("market", "bunkers", "usd_per_tonne_per_brent_dollar")


CURVE_HISTORY_FILE = ROOT / "data" / "seed" / "wti_curve_history.csv"


def curve_history() -> pd.Series:
    """Monthly average of the second-month minus first-month WTI futures price, 1985 to April 2024.

    Built from the EIA's RCLC1 and RCLC2 series, which the EIA stopped publishing in
    April 2024. Shown for scale only: it says nothing about today's curve.
    """
    table = pd.read_csv(CURVE_HISTORY_FILE, parse_dates=["month"], index_col="month")
    return table["m2_minus_m1"]
