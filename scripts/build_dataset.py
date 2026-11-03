# -*- coding: utf-8 -*-
"""清洗并重建亨通光电(600487)完整日线数据集

- 不复权价格: 腾讯行情 kline 接口
- 复权因子: 新浪 finance.sina.com.cn/realstock/company/sh600487/qfq.js|hfq.js
  前复权价 = 不复权价 / qfq因子
  后复权价 = 不复权价 × hfq因子
- 输出: output/600487_daily.csv, 600487_annual.csv, 600487_stats.json
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = Path("E:/Work/MakeMoney/data")
OUT = Path("E:/Work/MakeMoney/output")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
      "Referer": "https://finance.sina.com.cn/"}


def sina_factors(kind):
    txt = requests.get(f"https://finance.sina.com.cn/realstock/company/sh600487/{kind}.js",
                       headers=UA, timeout=25).text
    obj, _ = json.JSONDecoder().raw_decode(txt[txt.index("{"):])
    f = pd.DataFrame(obj["data"])
    f["d"] = pd.to_datetime(f["d"])
    f["f"] = f["f"].astype(float)
    return f.sort_values("d").reset_index(drop=True)


qfq_f, hfq_f = sina_factors("qfq"), sina_factors("hfq")

raw = pd.read_csv(BASE / "raw_600487_none.csv", parse_dates=["日期"]).sort_values("日期").reset_index(drop=True)
hfq_tx = pd.read_csv(BASE / "raw_600487_hfq.csv", parse_dates=["日期"])

# --- 补齐腾讯不复权接口缺失的 2007-09-04 (用腾讯后复权值按当时因子反推) ---
missing = sorted(set(hfq_tx["日期"]) - set(raw["日期"]))
if missing:
    for d in missing:
        row = hfq_tx[hfq_tx["日期"] == d].iloc[0]
        # 腾讯后复权/不复权 在相邻交易日的比值
        near = hfq_tx.merge(raw[["日期", "收盘"]], on="日期", how="inner")
        near["f"] = near["收盘_x"] / near["收盘_y"]
        f = near[near["日期"].between(d - pd.Timedelta(days=10), d + pd.Timedelta(days=10))]["f"].median()
        raw = pd.concat([raw, pd.DataFrame([{
            "日期": d,
            "开盘": round(row["开盘"] / f, 2), "收盘": round(row["收盘"] / f, 2),
            "最高": round(row["最高"] / f, 2), "最低": round(row["最低"] / f, 2),
            "成交量": row["成交量"],
        }])], ignore_index=True)
        print(f"补齐 {d.date()}: 收盘 {round(row['收盘'] / f, 2)}")
raw = raw.sort_values("日期").reset_index(drop=True)

# --- 合并复权因子 (取日期 <= t 的最后一个) ---
df = pd.merge_asof(raw, qfq_f.rename(columns={"d": "q_d", "f": "qfq因子"}), left_on="日期", right_on="q_d")
df = pd.merge_asof(df, hfq_f.rename(columns={"d": "h_d", "f": "hfq因子"}), left_on="日期", right_on="h_d")
df = df.drop(columns=["q_d", "h_d"])

for c in ["开盘", "最高", "最低", "收盘"]:
    df[f"{c}_qfq"] = (df[c] / df["qfq因子"]).round(3)
    df[f"{c}_hfq"] = (df[c] * df["hfq因子"]).round(3)

df["涨跌幅_qfq"] = (df["收盘_qfq"].pct_change() * 100).round(2)
df["涨跌幅_raw"] = (df["收盘"].pct_change() * 100).round(2)

daily = pd.DataFrame({
    "日期": df["日期"].dt.strftime("%Y-%m-%d"),
    "开盘": df["开盘"], "最高": df["最高"], "最低": df["最低"], "收盘": df["收盘"],
    "涨跌幅(%)": df["涨跌幅_raw"], "成交量(手)": df["成交量"].round(2),
    "开盘(前复权)": df["开盘_qfq"], "最高(前复权)": df["最高_qfq"],
    "最低(前复权)": df["最低_qfq"], "收盘(前复权)": df["收盘_qfq"],
    "涨跌幅(前复权%)": df["涨跌幅_qfq"],
    "收盘(后复权)": df["收盘_hfq"],
})
daily.to_csv(OUT / "600487_daily.csv", index=False, encoding="utf-8-sig")

# --- 年度汇总 (价格用前复权, 便于跨年比较; 另列不复权收盘) ---
df["年"] = df["日期"].dt.year
rows = []
for y, g in df.groupby("年"):
    prev = df[df["日期"] < g["日期"].iloc[0]]
    base = prev["收盘_qfq"].iloc[-1] if len(prev) else g["开盘_qfq"].iloc[0]
    rows.append({
        "年份": int(y),
        "交易日": len(g),
        "开盘(前复权)": g["开盘_qfq"].iloc[0],
        "最高(前复权)": g["最高_qfq"].max(),
        "最低(前复权)": g["最低_qfq"].min(),
        "收盘(前复权)": g["收盘_qfq"].iloc[-1],
        "收盘(不复权)": g["收盘"].iloc[-1],
        "年度涨跌幅(%)": round((g["收盘_qfq"].iloc[-1] / base - 1) * 100, 2),
        "年内振幅(%)": round((g["最高_qfq"].max() / g["最低_qfq"].min() - 1) * 100, 2),
        "成交量(万手)": round(g["成交量"].sum() / 1e4, 2),
    })
annual = pd.DataFrame(rows)
annual.to_csv(OUT / "600487_annual.csv", index=False, encoding="utf-8-sig")

# --- 关键统计 ---
d = df
first, last = d.iloc[0], d.iloc[-1]
years = (last["日期"] - first["日期"]).days / 365.25
ret_total = last["收盘_qfq"] / first["收盘_qfq"] - 1
running_max = d["收盘_qfq"].cummax()
dd = d["收盘_qfq"] / running_max - 1
trough = dd.idxmin()
peak = d.loc[:trough, "收盘_qfq"].idxmax()
imax, imin = d["最高"].idxmax(), d["最低"].idxmin()
best, worst = d["涨跌幅_qfq"].idxmax(), d["涨跌幅_qfq"].idxmin()
qmax, qmin = d["收盘_qfq"].idxmax(), d["收盘_qfq"].idxmin()

stats = {
    "首个交易日": str(first["日期"].date()), "最后交易日": str(last["日期"].date()),
    "交易日总数": int(len(d)),
    "上市首日开盘": float(first["开盘"]), "上市首日收盘": float(first["收盘"]),
    "最新收盘": float(last["收盘"]),
    "最新收盘(后复权)": float(last["收盘_hfq"]),
    "不复权累计涨幅(%)": round((last["收盘"] / first["收盘"] - 1) * 100, 2),
    "前复权累计涨幅(%)": round(ret_total * 100, 2),
    "年化收益率(%)": round(((1 + ret_total) ** (1 / years) - 1) * 100, 2),
    "持有年数": round(years, 2),
    "盘中最高价(不复权)": float(d.loc[imax, "最高"]), "盘中最高价日期": str(d.loc[imax, "日期"].date()),
    "盘中最低价(不复权)": float(d.loc[imin, "最低"]), "盘中最低价日期": str(d.loc[imin, "日期"].date()),
    "收盘最高(前复权)": float(d.loc[qmax, "收盘_qfq"]), "收盘最高日期": str(d.loc[qmax, "日期"].date()),
    "收盘最低(前复权)": float(d.loc[qmin, "收盘_qfq"]), "收盘最低日期": str(d.loc[qmin, "日期"].date()),
    "单日最大涨幅(%)": float(d.loc[best, "涨跌幅_qfq"]), "单日最大涨幅日期": str(d.loc[best, "日期"].date()),
    "单日最大跌幅(%)": float(d.loc[worst, "涨跌幅_qfq"]), "单日最大跌幅日期": str(d.loc[worst, "日期"].date()),
    "最大回撤(%)": round(dd.min() * 100, 2),
    "最大回撤峰值日": str(d.loc[peak, "日期"].date()),
    "最大回撤谷底日": str(d.loc[trough, "日期"].date()),
    "上涨年份": int((annual["年度涨跌幅(%)"] > 0).sum()),
    "下跌年份": int((annual["年度涨跌幅(%)"] <= 0).sum()),
    "除权除息次数": int((qfq_f["d"] > first["日期"]).sum()),
}
with open(OUT / "600487_stats.json", "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(annual.to_string(index=False))
print("\n" + json.dumps(stats, ensure_ascii=False, indent=2))

# 复权正确性检查: 前复权日涨跌幅 与 不复权日涨跌幅 的差异应只出现在除权日
diff = (d["涨跌幅_qfq"] - d["涨跌幅_raw"]).abs()
odd = d[diff > 0.3][["日期", "涨跌幅_raw", "涨跌幅_qfq"]]
print(f"\n非除权日的复权差异(>0.3pct) 条数: {len(odd)}")
print(odd.head(10).to_string(index=False))
