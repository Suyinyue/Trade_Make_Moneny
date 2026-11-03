"""Time each fundamentals call through the router, to find a slow or hanging endpoint."""

import datetime
import time

from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.router import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG

TODAY = datetime.date.today().strftime("%Y-%m-%d")
config = DEFAULT_CONFIG.copy()
config["data_cache_dir"] = r"E:\Work\MakeMoney\data\cache-ta"

with run_config(config):
    for label, method, args in (
        ("fundamentals", "get_fundamentals", ("600519.SS", TODAY)),
        ("balance_sheet", "get_balance_sheet", ("600519.SS", "quarterly", TODAY)),
        ("cashflow", "get_cashflow", ("600519.SS", "quarterly", TODAY)),
        ("income", "get_income_statement", ("600519.SS", "quarterly", TODAY)),
    ):
        started = time.time()
        try:
            out = route_to_vendor(method, *args)
            status = f"ok, {len(str(out))} chars"
        except Exception as exc:
            status = f"ERROR {type(exc).__name__}: {exc}"
        print(f"{label:14s} {time.time() - started:6.1f}s  {status}", flush=True)
