# -*- coding: utf-8 -*-
import pandas as pd

base = "E:/Work/MakeMoney/data"
d = {k: pd.read_csv(f"{base}/raw_600487_{k}.csv", parse_dates=["日期"]) for k in ["none", "qfq", "hfq"]}
for k, df in d.items():
    print(k, df.shape, df["日期"].min().date(), df["日期"].max().date())
    print(df.head(3).to_string())
    print(df.tail(3).to_string())
    print("缺失值:", df.isna().sum().to_dict())

n, q, h = d["none"], d["qfq"], d["hfq"]
print("\n日期差集 none-qfq:", sorted(set(q["日期"]) - set(n["日期"]))[:10])
print("qfq-hfq:", set(q["日期"]) ^ set(h["日期"]))

# 复权一致性: hfq 收益率 应约等于 qfq 收益率
m = q.merge(h, on="日期", suffixes=("_q", "_h"))
rq = m["收盘_q"].pct_change()
rh = m["收盘_h"].pct_change()
print("\n复权收益率最大偏差:", (rq - rh).abs().max())
print("不复权收益率与后复权最大偏差:", (n.merge(h, on='日期')['收盘_x'].pct_change() - n.merge(h, on='日期')['收盘_y'].pct_change()).abs().max())

# 原始接口是否有更多字段
import requests
r = requests.get("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600487,day,2026-09-01,2026-11-01,10,qfq", timeout=20)
print("\n原始返回样例:", r.json()["data"]["sh600487"]["qfqday"][-2:])
