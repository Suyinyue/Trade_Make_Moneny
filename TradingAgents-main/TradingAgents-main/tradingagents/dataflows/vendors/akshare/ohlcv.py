"""A-share OHLCV from akshare, cached and filtered so a run never reads ahead.

Mirrors ``vendors.yahoo.ohlcv.load_ohlcv``: five years per symbol, one cache
file per symbol, rows after the analysis date dropped, gaps carried forward for
indicators, and a stale frame rejected rather than fed to the analyst. All
signals are unadjusted-price independent because Sina's ``stock_zh_a_daily`` is
requested forward-adjusted (``qfq``), the A-share convention for research.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.files import replace_file
from tradingagents.dataflows.symbols import safe_ticker_component
from tradingagents.dataflows.vendors.akshare.common import (
    AShareSymbol,
    ak_retry,
    empty,
    resolve,
)

logger = logging.getLogger(__name__)

# A-share closures are longer than Western ones (Spring Festival and Golden Week
# each shut the market for most of a week), so a few more calendar days pass
# between the requested date and the last settled bar.
MAX_OHLCV_STALE_DAYS = 12

# A same-day cache may hold an intraday bar that is not the closing price; it is
# reused only briefly before the close is re-read (#1150 in the Yahoo vendor).
OHLCV_CACHE_TTL_SECONDS = 900

# Sina returns English columns; Eastmoney returns Chinese ones. Map both.
_COLUMN_ALIASES = {
    "date": "Date", "日期": "Date",
    "open": "Open", "开盘": "Open",
    "high": "High", "最高": "High",
    "low": "Low", "最低": "Low",
    "close": "Close", "收盘": "Close",
    "volume": "Volume", "成交量": "Volume",
}

_PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def _rename_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in frame.columns:
        key = str(col).strip()
        target = _COLUMN_ALIASES.get(key) or _COLUMN_ALIASES.get(key.lower())
        if target:
            rename[col] = target
    return frame.rename(columns=rename)


def _fetch_etf(ak, sym: AShareSymbol, start: str, end: str):
    """An ETF frame and whether its volume is in lots (100 shares) rather than shares."""
    sina = getattr(ak, "fund_etf_hist_sina", None)
    if sina is not None:
        frame = ak_retry(lambda: sina(symbol=sym.ak))
        if frame is not None and not frame.empty:
            return frame, False
    em = getattr(ak, "fund_etf_hist_em", None)
    if em is not None:
        frame = ak_retry(lambda: em(
            symbol=sym.code, period="daily", start_date=start, end_date=end, adjust="qfq",
        ))
        return frame, True        # Eastmoney reports volume in lots
    return None, False


def _fetch(sym: AShareSymbol, start: str, end: str):
    """Download one symbol's history: (frame, volume_in_lots)."""
    import akshare as ak

    if sym.kind == "index":
        # The Sina index endpoint takes no window and serves the full history.
        frame = ak_retry(lambda: ak.stock_zh_index_daily(symbol=sym.ak))
        return frame, False
    if sym.kind == "etf":
        return _fetch_etf(ak, sym, start, end)
    frame = ak_retry(lambda: ak.stock_zh_a_daily(
        symbol=sym.ak, start_date=start, end_date=end, adjust="qfq",
    ))
    return frame, False


def _normalize(frame: pd.DataFrame, volume_in_lots: bool) -> pd.DataFrame:
    """Normalize an akshare frame to Date/Open/High/Low/Close/Volume, date-sorted."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["Date", *_PRICE_COLUMNS])

    df = _rename_columns(frame)
    if "Date" not in df.columns:
        # Some endpoints leave the date on the index.
        df = _rename_columns(df.reset_index())
    if "Date" not in df.columns:
        return pd.DataFrame(columns=["Date", *_PRICE_COLUMNS])

    df = df.loc[:, ~df.columns.duplicated()].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    kept = [c for c in _PRICE_COLUMNS if c in df.columns]
    if "Close" not in kept:
        return pd.DataFrame(columns=["Date", *_PRICE_COLUMNS])
    df[kept] = df[kept].apply(pd.to_numeric, errors="coerce")
    if volume_in_lots and "Volume" in df.columns:
        df["Volume"] = df["Volume"] * 100
    return df[["Date", *kept]].sort_values("Date").reset_index(drop=True)


def _cache_is_fresh(data_file, as_of_dt, now) -> bool:
    """Whether the cached download can serve this request (same rule as Yahoo)."""
    written = pd.Timestamp.fromtimestamp(os.path.getmtime(data_file))
    if written.date() != now.date():
        return False
    return as_of_dt.date() < now.date() or (now - written).total_seconds() <= OHLCV_CACHE_TTL_SECONDS


def _fill_price_gaps(data: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with no close and carry the remaining gaps forward."""
    cols = [c for c in _PRICE_COLUMNS if c in data.columns]
    data = data.dropna(subset=["Close"]).copy()
    data[cols] = data[cols].ffill().bfill()
    return data


def _assert_not_stale(data: pd.DataFrame, as_of_date: str, sym: AShareSymbol) -> None:
    """Reject a frame whose latest row is far older than the requested date."""
    if data is None or data.empty:
        return
    requested = pd.to_datetime(as_of_date, errors="coerce")
    if pd.isna(requested):
        return
    latest = pd.to_datetime(data["Date"], errors="coerce").max()
    if pd.isna(latest):
        return
    stale_days = (requested.normalize() - latest.normalize()).days
    if stale_days > MAX_OHLCV_STALE_DAYS:
        raise NoMarketDataError(
            sym.yahoo, sym.yahoo,
            f"latest row is {latest.date()}, {stale_days} days before the requested "
            f"{requested.date()} (stale) — refusing to use it",
        )


def load_ohlcv(symbol: str, as_of_date: str, fill_gaps: bool = True) -> pd.DataFrame:
    """OHLCV for ``symbol`` up to ``as_of_date``, from akshare, cached per symbol.

    Raises ``NoMarketDataError`` when the symbol is not an A-share instrument or
    the vendor has no rows for it, and ``VendorUnavailableError`` when the
    request itself failed — the two answers the router distinguishes.
    """
    sym = resolve(symbol)
    safe_symbol = safe_ticker_component(sym.yahoo)

    config = get_config()
    as_of_dt = pd.to_datetime(as_of_date).normalize()
    now = pd.Timestamp.today()
    start_str = (now - pd.DateOffset(years=5)).strftime("%Y%m%d")
    end_str = (now + pd.Timedelta(days=1)).strftime("%Y%m%d")

    os.makedirs(config["data_cache_dir"], exist_ok=True)
    data_file = os.path.join(config["data_cache_dir"], f"{safe_symbol}-akshare-data.csv")

    data = None
    if os.path.exists(data_file):
        cached = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
        if not cached.empty and "Close" in cached.columns and _cache_is_fresh(data_file, as_of_dt, now):
            data = cached

    if data is None:
        frame, volume_in_lots = _fetch(sym, start_str, end_str)
        downloaded = _normalize(frame, volume_in_lots)
        if downloaded.empty:
            raise empty(symbol, sym, "price rows")
        replace_file(data_file, lambda temp: downloaded.to_csv(temp, index=False, encoding="utf-8"))
        data = downloaded

    data = _normalize(data, False)

    # Point-in-time: nothing after the analysis date reaches the agent.
    data = data[data["Date"] <= as_of_dt]

    if not data.empty and pd.isna(data["Close"].iloc[-1]):
        settled = data["Close"].notna().to_numpy().nonzero()[0]
        if settled.size == 0:
            raise NoMarketDataError(symbol, sym.yahoo, "no bar in range has a closing price")
        logger.warning(
            "%s: trailing bar(s) have no closing price; using %s as the latest close.",
            sym.yahoo, data["Date"].iloc[settled[-1]].date(),
        )

    data = _fill_price_gaps(data) if fill_gaps else data.dropna(subset=["Close"]).copy()
    _assert_not_stale(data, as_of_date, sym)
    return data
