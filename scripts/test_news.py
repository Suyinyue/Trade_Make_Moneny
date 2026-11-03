"""Check the per-stock news fallback across a recent and an older window."""

from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.router import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["data_cache_dir"] = r"E:\Work\MakeMoney\data\cache-ta"

with run_config(config):
    print("--- older window (cninfo fallback expected) ---", flush=True)
    print(route_to_vendor("get_news", "600519.SS", "2026-10-01", "2026-10-23")[:1500], flush=True)
    print("\n--- recent window (Eastmoney news expected) ---", flush=True)
    print(route_to_vendor("get_news", "600519.SS", "2026-10-26", "2026-10-30")[:600], flush=True)
