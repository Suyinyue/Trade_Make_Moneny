# -*- coding: utf-8 -*-
"""抓取亨通光电与同业/指数的近半年日线, 计算区间表现"""
import time
from datetime import datetime

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"}
URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
SYMBOLS = {
    "sh600487": "亨通光电",
    "sh601869": "长飞光纤",
    "sh600522": "中天科技",
    "sh600498": "烽火通信",
    "sz300308": "中际旭创",
    "sz300502": "新易盛",
    "sz300394": "天孚通信",
    "sh000001": "上证指数",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
}
START, END = "2026-04-01", "2026-11-01"

out = {}
for sym, name in SYMBOLS.items():
    for attempt in range(4):
        try:
            r = requests.get(URL, params={"param": f"{sym},day,{START},{END},400"},
                             headers=UA, timeout=25)
            data = r.json()["data"][sym]
            rows = data.get("day") or data.get("qfqday")
            df = pd.DataFrame([x[:6] for x in rows],
                              columns=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
            df["日期"] = pd.to_datetime(df["日期"])
            df["收盘"] = df["收盘"].astype(float)
            out[sym] = df.sort_values("日期").reset_index(drop=True)
            print(f"{name:8s} {len(df):4d} 行 {df['日期'].min().date()} ~ {df['日期'].max().date()}")
            break
        except Exception as e:
            print(f"{name} 失败 {attempt+1}: {e}")
            time.sleep(2)
    time.sleep(0.4)

# 计算指标
peak_window = ("2026-06-01", "2026-06-30")
res = []
for sym, df in out.items():
    s = df.set_index("日期")["收盘"]
    peak_day = s[(s.index >= peak_window[0]) & (s.index <= peak_window[1])].idxmax()
    peak = s.loc[peak_day]
    last = s.iloc[-1]

    def ret(a, b):
        sa = s[s.index <= pd.Timestamp(a)]
        sb = s[s.index <= pd.Timestamp(b)]
        if sa.empty or sb.empty:
            return None
        return (sb.iloc[-1] / sa.iloc[-1] - 1) * 100

    res.append({
        "名称": SYMBOLS[sym],
        "年内高点日": peak_day.strftime("%m-%d"),
        "高点": round(peak, 2),
        "最新": round(last, 2),
        "高点回撤%": round((last / peak - 1) * 100, 2),
        "8月%": round(ret("2026-07-31", "2026-08-31") or 0, 2),
        "9月%": round(ret("2026-08-31", "2026-09-30") or 0, 2),
        "10月%": round(ret("2026-09-30", "2026-10-30") or 0, 2),
        "9/24后%": round(ret("2026-09-24", "2026-10-30") or 0, 2),
        "10/28后%": round(ret("2026-10-28", "2026-10-30") or 0, 2),
    })

r = pd.DataFrame(res)
print("\n" + r.to_string(index=False))
r.to_csv("E:/Work/MakeMoney/output/peer_compare.csv", index=False, encoding="utf-8-sig")

# 亨通量能
h = out["sh600487"].set_index("日期")
h["vol20"] = h["成交量"].rolling(20).mean()
print("\n亨通成交量(手) 关键日:")
for d in ["2026-06-25", "2026-08-27", "2026-09-24", "2026-09-28", "2026-10-19", "2026-10-28", "2026-10-29", "2026-10-30"]:
    if pd.Timestamp(d) in h.index:
        row = h.loc[pd.Timestamp(d)]
        print(f"  {d} 收盘{row['收盘']:>7.2f}  量{row['成交量']/1e4:>8.1f}万手  20日均量{row['vol20']/1e4:>8.1f}万手")
