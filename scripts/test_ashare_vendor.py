"""Exercise the akshare vendor through the router, the way the agents call it."""

import datetime

from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.router import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.vendors.yahoo.snapshot import build_verified_market_snapshot

AS_OF = "2026-10-30"
TODAY = datetime.date.today().strftime("%Y-%m-%d")

config = DEFAULT_CONFIG.copy()
config["data_cache_dir"] = r"E:\Work\MakeMoney\data\cache-ta"
config["results_dir"] = r"E:\Work\MakeMoney\output\tradingagents"


def show(label, text, limit=900):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    text = str(text)
    print(text[:limit])
    if len(text) > limit:
        print(f"... [{len(text)} chars total]")


with run_config(config):
    show("get_stock_data 600519.SS", route_to_vendor(
        "get_stock_data", "600519.SS", "2026-09-20", AS_OF))
    show("get_stock_data 000001.SZ", route_to_vendor(
        "get_stock_data", "000001.SZ", "2026-09-20", AS_OF))
    show("get_stock_data index 000001.SS", route_to_vendor(
        "get_stock_data", "000001.SS", "2026-09-20", AS_OF))
    show("get_indicators rsi", route_to_vendor(
        "get_indicators", "600519.SS", "rsi", AS_OF, 10))
    show("get_news 600519.SS", route_to_vendor(
        "get_news", "600519.SS", "2026-10-01", AS_OF))
    show("get_global_news", route_to_vendor(
        "get_global_news", AS_OF, 7, 5))
    show("get_fundamentals today", route_to_vendor("get_fundamentals", "600519.SS", TODAY))
    show("get_fundamentals historical", route_to_vendor("get_fundamentals", "600519.SS", AS_OF))
    show("get_balance_sheet", route_to_vendor(
        "get_balance_sheet", "600519.SS", "quarterly", AS_OF), limit=1200)
    show("snapshot", build_verified_market_snapshot("600519.SS", AS_OF), limit=1500)
    show("US ticker falls through to yfinance", route_to_vendor(
        "get_stock_data", "AAPL", "2026-09-20", AS_OF))

print("\nALL DONE")
