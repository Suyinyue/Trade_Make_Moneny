# -*- coding: utf-8 -*-
"""补充统计: 大波段、极端交易日、区间收益、除权事件"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("E:/Work/MakeMoney/output")
d = pd.read_csv(OUT / "600487_daily.csv", parse_dates=["日期"])
d = d.sort_values("日期").reset_index(drop=True)

# --- 1. 复权因子跳变(除权除息事件) ---
import requests, re
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
txt = requests.get("https://finance.sina.com.cn/realstock/company/sh600487/qfq.js", headers=UA, timeout=20).text
ev = pd.DataFrame(json.JSONDecoder().raw_decode(txt[txt.index("{"):])[0]["data"])
ev["d"] = pd.to_datetime(ev["d"])
ev["qfq因子"] = ev["f"].astype(float)
ev = ev.sort_values("d").reset_index(drop=True)
# 事件日的因子变化: 因子在事件日起生效, 故相对上一事件的变化 = 该次除权除息的调整幅度
ev["相对上次调整(%)"] = (ev["qfq因子"] / ev["qfq因子"].shift(1) - 1).mul(100).round(2)
# 剔除上市日(仅为基准因子, 非除权除息事件)
ev = ev[ev["d"] > d["日期"].iloc[0]].reset_index(drop=True)
print("除权除息事件:")
print(ev[["d", "qfq因子", "相对上次调整(%)"]].to_string(index=False))

# --- 2. 大波段 (zigzag, 反向幅度>=40%) ---
px = d.set_index("日期")["收盘(前复权)"]
th = 0.40
pivots = [(px.index[0], px.iloc[0], "start")]
trend, ext_i, ext_v = 0, 0, px.iloc[0]
for i in range(1, len(px)):
    v = px.iloc[i]
    if trend >= 0:
        if v > ext_v:
            ext_i, ext_v = i, v
        elif v < ext_v * (1 - th):
            pivots.append((px.index[ext_i], ext_v, "peak"))
            trend, ext_i, ext_v = -1, i, v
    else:
        if v < ext_v:
            ext_i, ext_v = i, v
        elif v > ext_v * (1 + th):
            pivots.append((px.index[ext_i], ext_v, "trough"))
            trend, ext_i, ext_v = 1, i, v
pivots.append((px.index[-1], px.iloc[-1], "end"))
# 去掉重复/倒退点
clean = [pivots[0]]
for p in pivots[1:]:
    if p[0] > clean[-1][0]:
        clean.append(p)
pivots = clean
swings = []
for (d1, v1, _), (d2, v2, _) in zip(pivots, pivots[1:]):
    swings.append({"起点": str(d1.date()), "终点": str(d2.date()), "起点价": round(float(v1), 3),
                   "终点价": round(float(v2), 3), "涨跌幅(%)": round((v2 / v1 - 1) * 100, 2),
                   "历时(月)": round((d2 - d1).days / 30.44, 1)})
sw = pd.DataFrame(swings)
print("\n大波段(>=40%):")
print(sw.to_string(index=False))

# --- 3. 极端交易日(剔除除权日) ---
exd = set(ev["d"])
q = d.copy()
q["除权日"] = q["日期"].isin(exd)
norm = q[~q["除权日"]]
best = norm.nlargest(5, "涨跌幅(前复权%)")[["日期", "涨跌幅(前复权%)", "收盘"]]
worst = norm.nsmallest(5, "涨跌幅(前复权%)")[["日期", "涨跌幅(前复权%)", "收盘"]]
print("\n最大单日涨幅:")
print(best.to_string(index=False))
print("\n最大单日跌幅:")
print(worst.to_string(index=False))

# --- 4. 区间收益 ---
def ret(a, b):
    s = px[(px.index >= a) & (px.index <= b)]
    return round((s.iloc[-1] / s.iloc[0] - 1) * 100, 2), s.index[0].date(), s.index[-1].date()

periods = {
    "近 1 年（2025-10-30 起）": ret("2025-10-30", "2026-10-30"),
    "近 3 年（2023-10-30 起）": ret("2023-10-30", "2026-10-30"),
    "近 5 年（2021-10-29 起）": ret("2021-10-29", "2026-10-30"),
    "近 10 年（2016-10-31 起）": ret("2016-10-31", "2026-10-30"),
    "上市以来（2003-08-22 起）": ret("2003-08-22", "2026-10-30"),
}
print("\n区间收益:")
for k, v in periods.items():
    print(f"{k}: {v[0]}%  ({v[1]} ~ {v[2]})")

# --- 5. 年度涨跌幅排序 ---
a = pd.read_csv(OUT / "600487_annual.csv")
print("\n最佳年份:")
print(a.nlargest(5, "年度涨跌幅(%)")[["年份", "年度涨跌幅(%)", "最高(前复权)", "收盘(前复权)"]].to_string(index=False))
print("\n最差年份:")
print(a.nsmallest(5, "年度涨跌幅(%)")[["年份", "年度涨跌幅(%)", "最低(前复权)", "收盘(前复权)"]].to_string(index=False))

# --- 6. 回撤前十 ---
run = px.cummax()
dd = (px / run - 1) * 100
order = dd.sort_values().index
print("\n最大回撤:", round(dd.min(), 2), "底:", dd.idxmin().date())

# --- 7. 年度波动
print("\n末年数据:", d.iloc[-1][["日期", "收盘", "收盘(前复权)"]].to_dict())
print("首年数据:", d.iloc[0][["日期", "开盘", "收盘", "收盘(前复权)"]].to_dict())

# 保存
extras = {
    "events": [{"日期": str(r["d"].date()), "调整幅度(%)": (None if pd.isna(r["相对上次调整(%)"]) else float(r["相对上次调整(%)"]))} for _, r in ev.iterrows()],
    "swings": swings, "periods": {k: v[0] for k, v in periods.items()},
    "best_days": best.to_dict("records"), "worst_days": worst.to_dict("records"),
}
with open(OUT / "600487_extras.json", "w", encoding="utf-8") as f:
    json.dump(extras, f, ensure_ascii=False, indent=2, default=str)
ev.to_csv(OUT / "600487_events.csv", index=False, encoding="utf-8-sig")
sw.to_csv(OUT / "600487_swings.csv", index=False, encoding="utf-8-sig")
