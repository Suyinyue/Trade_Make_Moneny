# -*- coding: utf-8 -*-
"""对比关键日同业的涨跌幅, 判断个股事件是否被板块放大"""
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0"}
URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
SYMBOLS = {
    "sh600487": "亨通光电", "sh601869": "长飞光纤", "sh600522": "中天科技",
    "sh600498": "烽火通信", "sz300308": "中际旭创", "sz300502": "新易盛",
    "sz300394": "天孚通信",
}
DATES = ["2026-09-24", "2026-09-28", "2026-10-19", "2026-10-28", "2026-10-29", "2026-10-30"]

rows = []
for sym, name in SYMBOLS.items():
    r = requests.get(URL, params={"param": f"{sym},day,2026-09-01,2026-11-01,200"},
                     headers=UA, timeout=25)
    data = r.json()["data"][sym]["day"]
    df = pd.DataFrame([x[:3] for x in data], columns=["日期", "开盘", "收盘"])
    df["收盘"] = df["收盘"].astype(float)
    df["日期"] = pd.to_datetime(df["日期"])
    s = df.set_index("日期")["收盘"].sort_index()
    row = {"名称": name}
    for d in DATES:
        pct = s.pct_change().get(pd.Timestamp(d))
        row[d[5:]] = None if pd.isna(pct) else round(pct * 100, 2)
    rows.append(row)

print(pd.DataFrame(rows).to_string(index=False))
