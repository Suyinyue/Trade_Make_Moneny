# -*- coding: utf-8 -*-
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0"}
r = requests.get("https://web.ifzq.gtimg.cn/appstock/app/kline/kline",
                 params={"param": "sh600487,day,2026-04-01,2026-11-01,400"},
                 headers=UA, timeout=25)
rows = r.json()["data"]["sh600487"]["day"]
df = pd.DataFrame([x[:6] for x in rows], columns=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
df["成交量"] = pd.to_numeric(df["成交量"])
df["收盘"] = pd.to_numeric(df["收盘"])
df["日期"] = pd.to_datetime(df["日期"])
df = df.set_index("日期").sort_index()
df["vol20"] = df["成交量"].rolling(20).mean()

print("日期        收盘      成交量(万手)  20日均量(万手)  倍数")
for d in ["2026-06-25", "2026-08-27", "2026-09-24", "2026-09-28",
          "2026-10-19", "2026-10-28", "2026-10-29", "2026-10-30"]:
    t = pd.Timestamp(d)
    if t in df.index:
        row = df.loc[t]
        print(f"{d}  {row['收盘']:7.2f}  {row['成交量']/1e4:10.1f}  {row['vol20']/1e4:12.1f}  {row['成交量']/row['vol20']:5.2f}")

print("\n历史最大量:", df["成交量"].idxmax().date(), round(df["成交量"].max() / 1e4, 1), "万手")
print("6月峰值日量:", round(df.loc['2026-06-25', '成交量'] / 1e4, 1), "万手")
print("10月均量:", round(df.loc['2026-10-01':'2026-10-31', '成交量'].mean() / 1e4, 1), "万手")
print("8月均量:", round(df.loc['2026-08-01':'2026-08-31', '成交量'].mean() / 1e4, 1), "万手")
