# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

RAW = Path(r"E:\Work\MakeMoney\data\raw")

def load(code):
    df = pd.read_csv(RAW / f"{code}.csv", parse_dates=["date"]).sort_values("date").set_index("date")
    return df["close"]

for code, name in [("sh000300", "CSI300"), ("sh000001", "SHCOMP"), ("sz399006", "CHINEXT")]:
    c = load(code)
    w = c.resample("W-FRI").last().dropna()
    last = w.tail(14)
    rets = last.pct_change().round(4)
    downs = 0
    for v in rets.iloc[::-1]:
        if v < 0:
            downs += 1
        else:
            break
    print(f"\n{name}: consecutive down weeks = {downs}")
    print(pd.DataFrame({"close": last.round(2), "wchg": rets}).to_string())

print("\n--- October 2026 monthly returns ---")
for code, name in [("sh000001", "SHCOMP"), ("sh000300", "CSI300"), ("sz399006", "CHINEXT"),
                   ("sh000688", "STAR50"), ("sh000015", "SSE_DIV"), ("sh000852", "CSI1000")]:
    c = load(code)
    sep = c[c.index <= "2026-09-30"].iloc[-1]
    oct_ret = c.iloc[-1] / sep - 1
    # 历史单月跌幅排名
    m = c.resample("ME").last().pct_change().dropna()
    m = m[m.index >= "2000-01-01"]
    rank = (m < oct_ret).sum() + 1
    print(f"{name}: Oct2026={oct_ret:.2%}, all-time monthly rank(2000+)={rank}/{len(m)}")

print("\n--- 2026 monthly path SHCOMP ---")
c = load("sh000001")
m = c.resample("ME").last()
print(m[m.index >= "2025-10-01"].round(2).to_string())
