"""Second half of the vendor check: fundamentals, statements, snapshot."""

import datetime
import sys

from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.router import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.vendors.yahoo.snapshot import build_verified_market_snapshot

AS_OF = "2026-10-30"
TODAY = datetime.date.today().strftime("%Y-%m-%d")

config = DEFAULT_CONFIG.copy()
config["data_cache_dir"] = r"E:\Work\MakeMoney\data\cache-ta"
config["results_dir"] = r"E:\Work\MakeMoney\output\tradingagents"


def show(label, text, limit=1800):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}", flush=True)
    text = str(text)
    print(text[:limit], flush=True)
    if len(text) > limit:
        print(f"... [{len(text)} chars total]", flush=True)


with run_config(config):
    show("get_fundamentals TODAY", route_to_vendor("get_fundamentals", "600519.SS", TODAY))
    show("get_fundamentals HISTORICAL", route_to_vendor("get_fundamentals", "600519.SS", AS_OF))
    show("get_balance_sheet", route_to_vendor(
        "get_balance_sheet", "600519.SS", "quarterly", AS_OF), limit=1200)
    show("snapshot", build_verified_market_snapshot("600519.SS", AS_OF), limit=2000)
    show("daily indicators for an index", route_to_vendor(
        "get_indicators", "000001.SS", "close_50_sma", AS_OF, 5))

sys.stdout.flush()
print("\nALL DONE", flush=True)
