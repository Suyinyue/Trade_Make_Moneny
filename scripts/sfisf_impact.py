# -*- coding: utf-8 -*-
"""互换便利(SFISF)关键时点: 亨通光电与沪深300/中证500的当日表现"""
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0"}
URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
SYMS = {"sh600487": "亨通光电", "sh000300": "沪深300", "sh000905": "中证500", "sz399006": "创业板指"}


def load(sym, start="2024-09-01", end="2026-11-05"):
    r = requests.get(URL, params={"param": f"{sym},day,{start},{end},600"}, headers=UA, timeout=25)
    data = r.json()["data"][sym]["day"]
    df = pd.DataFrame([x[:3] for x in data], columns=["日期", "开盘", "收盘"])
    df["收盘"] = df["收盘"].astype(float)
    df["日期"] = pd.to_datetime(df["日期"])
    return df.set_index("日期")["收盘"].sort_index()


series = {name: load(sym) for sym, name in SYMS.items()}
print({k: (v.index.min().date(), v.index.max().date(), len(v)) for k, v in series.items()})

events = ["2024-09-24", "2024-10-10", "2024-10-18", "2024-10-21", "2025-01-02", "2026-11-02", "2026-11-03"]
print("\n日期        亨通     沪深300   中证500   创业板   相对300")
for d in events:
    t = pd.Timestamp(d)
    row = []
    for name in SYMS.values():
        s = series[name]
        pct = s.pct_change().get(t)
        row.append(None if pd.isna(pct) else round(pct * 100, 2))
    rel = "—" if row[0] is None or row[1] is None else f"{row[0]-row[1]:+.2f}pct"
    print(f"{d}  {str(row[0]):>7}  {str(row[1]):>7}  {str(row[2]):>7}  {str(row[3]):>7}  {rel:>9}")

print("\n最近 6 个交易日:")
h = series["亨通光电"]
print(h.tail(6).to_string())
