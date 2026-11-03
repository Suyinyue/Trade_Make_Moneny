"""Check the latest A-share prices and the DeepSeek endpoint with the proxy bypassed."""

import os

import requests

from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.router import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG

print("proxies seen by requests:", requests.utils.getproxies(), flush=True)

config = DEFAULT_CONFIG.copy()
config["data_cache_dir"] = r"E:\Work\MakeMoney\data\cache-ta"

with run_config(config):
    out = route_to_vendor("get_stock_data", "600487.SS", "2026-10-28", "2026-11-03")
    print(out[-600:], flush=True)

r = requests.get(
    "https://api.deepseek.com/models",
    headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
    timeout=20,
)
print("deepseek:", r.status_code, [m["id"] for m in r.json().get("data", [])], flush=True)
