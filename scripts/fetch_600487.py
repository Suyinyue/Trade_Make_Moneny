# -*- coding: utf-8 -*-
"""下载亨通光电(600487)上市以来全部日线行情: 不复权 / 前复权 / 后复权

数据源: 腾讯行情 web.ifzq.gtimg.cn (分批向前翻页)
"""
import json
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
URLS = {
    "kline": "https://web.ifzq.gtimg.cn/appstock/app/kline/kline",
    "fqkline": "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
}
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Referer": "https://gu.qq.com/sh600487/gp",
}
END = datetime(2026, 11, 1)
START = datetime(2003, 1, 1)
LIMIT = 640


def fetch_page(kind, fq, end_date):
    """kind: fqkline(复权) / kline(不复权); fq: qfq/hfq/'' ; 返回按日期升序的列表"""
    param = f"sh600487,day,{START:%Y-%m-%d},{end_date:%Y-%m-%d},{LIMIT},{fq}"
    if kind == "kline":
        param = f"sh600487,day,{START:%Y-%m-%d},{end_date:%Y-%m-%d},{LIMIT}"
    for attempt in range(5):
        try:
            r = requests.get(URLS[kind], params={"param": param},
                             headers=HEADERS, timeout=30)
            r.raise_for_status()
            payload = r.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"code={payload.get('code')} msg={payload.get('msg')}")
            node = payload["data"]["sh600487"]
            key = f"{fq}day" if kind == "fqkline" else "day"
            rows = node.get(key) or node.get("day") or []
            return rows
        except Exception as e:
            print(f"    {kind}/{fq} {end_date:%Y-%m-%d} 第{attempt+1}次失败: {e}")
            time.sleep(3 + 2 * attempt)
    raise SystemExit(f"{kind}/{fq} 抓取失败, end={end_date:%Y-%m-%d}")


def fetch_all(kind, fq):
    end_date, pages, seen = END, [], set()
    while True:
        rows = fetch_page(kind, fq, end_date)
        if not rows:
            break
        new = [r for r in rows if r[0] not in seen]
        pages.extend(new)
        for r in new:
            seen.add(r[0])
        earliest = min(r[0] for r in rows)
        print(f"  {kind}/{fq}: {earliest} ~ {max(r[0] for r in rows)}  ({len(rows)} 条, 累计 {len(pages)})")
        if len(rows) < LIMIT or earliest <= f"{START:%Y-%m-%d}":
            break
        end_date = datetime.strptime(earliest, "%Y-%m-%d") - timedelta(days=1)
        time.sleep(0.6)
    df = pd.DataFrame(pages)
    if df.empty:
        raise SystemExit(f"{kind}/{fq} 无数据")
    df = df.iloc[:, :6]
    df.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量"]
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["日期"] = pd.to_datetime(df["日期"])
    return df.sort_values("日期").drop_duplicates("日期").reset_index(drop=True)


for kind, fq, name in [("kline", "", "none"), ("fqkline", "qfq", "qfq"), ("fqkline", "hfq", "hfq")]:
    print(f"[{name}] 开始下载")
    df = fetch_all(kind, fq)
    path = f"{OUT}/raw_600487_{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[{name}] 完成: {len(df)} 行, {df['日期'].min().date()} ~ {df['日期'].max().date()} -> {path}\n")
