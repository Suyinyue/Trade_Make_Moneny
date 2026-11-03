# -*- coding: utf-8 -*-
"""光模块/光通信核心标的近期表现快照（数据源：新浪，经 AKShare）。"""
import sys
import time
from pathlib import Path

import pandas as pd

RAW = Path(r"E:\Work\MakeMoney\data\raw_optical")
RAW.mkdir(parents=True, exist_ok=True)

STOCKS = [
    ("sz300308", "中际旭创", "光模块"),
    ("sz300502", "新易盛", "光模块"),
    ("sz300394", "天孚通信", "光器件"),
    ("sz002281", "光迅科技", "光模块/器件"),
    ("sz000988", "华工科技", "光模块"),
    ("sz300570", "太辰光", "光器件/MPO"),
    ("sh688205", "德科立", "光模块"),
    ("sh688498", "源杰科技", "光芯片"),
    ("sh688313", "仕佳光子", "光芯片/器件"),
    ("sh603083", "剑桥科技", "光模块"),
    ("sz300548", "博创科技", "光器件"),
    ("sh600487", "亨通光电", "光纤光缆/海缆"),
]


def fetch(code: str) -> pd.DataFrame:
    cache = RAW / f"{code}.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"])
    import akshare as ak

    last = None
    for i in range(3):
        try:
            df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
            df.to_csv(cache, index=False, encoding="utf-8-sig")
            return pd.read_csv(cache, parse_dates=["date"])
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    raise RuntimeError(f"{code}: {last}")


rows = []
for code, name, seg in STOCKS:
    try:
        df = fetch(code).sort_values("date").set_index("date")
    except Exception as e:  # noqa: BLE001
        print(f"{code} {name} 取数失败: {e}")
        continue
    c = df["close"]
    last = c.iloc[-1]
    y = c[c.index >= "2026-01-01"]
    peak = y.max()
    peak_date = y.idxmax()
    base = c[c.index < "2026-01-01"].iloc[-1]
    sep = c[c.index <= "2026-09-30"].iloc[-1]
    rows.append(dict(
        name=name, seg=seg, code=code, last=round(last, 2), date=str(c.index[-1].date()),
        d1=round(c.iloc[-1] / c.iloc[-2] - 1, 4),
        r5=round(c.iloc[-1] / c.iloc[-6] - 1, 4),
        r20=round(c.iloc[-1] / c.iloc[-21] - 1, 4),
        oct=round(last / sep - 1, 4),
        ytd=round(last / base - 1, 4),
        peak=round(peak, 2), peak_date=str(peak_date.date()),
        dd=round(last / peak - 1, 4),
        off_low=round(last / y.min() - 1, 4),
    ))

out = pd.DataFrame(rows)
out = out.sort_values("oct")
print(out.to_string(index=False))
