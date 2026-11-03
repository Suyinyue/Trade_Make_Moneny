"""A-share price rows and technical indicators, served from akshare.

The two functions the router calls for ``core_stock_apis`` and
``technical_indicators``. Their output is shaped like the Yahoo vendor's so the
analysts read the same report regardless of which vendor answered; only the
header names the source, and only the loader differs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.vendors.akshare.common import resolve
from tradingagents.dataflows.vendors.akshare.ohlcv import load_ohlcv

# Kept in step with the Yahoo vendor's descriptions: the indicator names are the
# stockstats column names, and the model is told the same thing about each.
INDICATOR_DESCRIPTIONS = {
    "close_50_sma": (
        "50 SMA: A medium-term trend indicator. "
        "Usage: Identify trend direction and serve as dynamic support/resistance. "
        "Tips: It lags price; combine with faster indicators for timely signals."
    ),
    "close_200_sma": (
        "200 SMA: A long-term trend benchmark. "
        "Usage: Confirm overall market trend and identify golden/death cross setups. "
        "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
    ),
    "close_10_ema": (
        "10 EMA: A responsive short-term average. "
        "Usage: Capture quick shifts in momentum and potential entry points. "
        "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
    ),
    "macd": (
        "MACD: Computes momentum via differences of EMAs. "
        "Usage: Look for crossovers and divergence as signals of trend changes. "
        "Tips: Confirm with other indicators in low-volatility or sideways markets."
    ),
    "macds": (
        "MACD Signal: An EMA smoothing of the MACD line. "
        "Usage: Use crossovers with the MACD line to trigger trades. "
        "Tips: Should be part of a broader strategy to avoid false positives."
    ),
    "macdh": (
        "MACD Histogram: Shows the gap between the MACD line and its signal. "
        "Usage: Visualize momentum strength and spot divergence early. "
        "Tips: Can be volatile; complement with additional filters in fast-moving markets."
    ),
    "rsi": (
        "RSI: Measures momentum to flag overbought/oversold conditions. "
        "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
        "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
    ),
    "boll": (
        "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
        "Usage: Acts as a dynamic benchmark for price movement. "
        "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
    ),
    "boll_ub": (
        "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
        "Usage: Signals potential overbought conditions and breakout zones. "
        "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
    ),
    "boll_lb": (
        "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
        "Usage: Indicates potential oversold conditions. "
        "Tips: Use additional analysis to avoid false reversal signals."
    ),
    "atr": (
        "ATR: Averages true range to measure volatility. "
        "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
        "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
    ),
    "vwma": (
        "VWMA: A moving average weighted by volume. "
        "Usage: Confirm trends by integrating price action with volume data. "
        "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
    ),
    "mfi": (
        "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
        "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
        "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
    ),
}


def get_stock_data_akshare(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):
    """OHLCV rows between the two dates as CSV, forward-adjusted (qfq)."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    sym = resolve(symbol)

    data = load_ohlcv(symbol, end_date, fill_gaps=False)
    window = data[(data["Date"] >= start_dt) & (data["Date"] <= end_dt)].copy()
    if window.empty:
        raise NoMarketDataError(
            symbol, sym.yahoo, f"no rows between {start_date} and {end_date}"
        )

    window["Date"] = window["Date"].dt.strftime("%Y-%m-%d")
    csv_string = window.set_index("Date").to_csv()

    label = f"{sym.yahoo} ({sym.kind}, akshare)"
    header = f"# Stock data for {label} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(window)}\n"
    if sym.is_index:
        header += "# Index level; Volume is in shares.\n\n"
    else:
        header += "# Prices are forward-adjusted (qfq); Volume is in shares.\n\n"
    return header + csv_string


def get_stock_stats_indicators_window_akshare(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    as_of_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    """One indicator over the trailing window, computed with stockstats."""
    indicator = indicator.strip().lower()
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: "
            f"{list(INDICATOR_DESCRIPTIONS)}"
        )

    end_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
    before = end_dt - relativedelta(days=look_back_days)

    data = load_ohlcv(symbol, as_of_date)
    frame = wrap(data)
    frame["Date"] = frame["Date"].dt.strftime("%Y-%m-%d")
    frame[indicator]  # triggers stockstats to calculate the column

    values = {}
    for row_date, value in zip(frame["Date"], frame[indicator]):
        values[row_date] = "N/A" if pd.isna(value) else str(value)

    lines = []
    current = end_dt
    while current >= before:
        day = current.strftime("%Y-%m-%d")
        lines.append(f"{day}: {values.get(day, 'N/A: Not a trading day (weekend or holiday)')}")
        current -= relativedelta(days=1)

    return (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {as_of_date}:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + INDICATOR_DESCRIPTIONS[indicator]
    )
