# -*- coding: utf-8 -*-
import requests, time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
tests = [
    ("em", "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600487&fields1=f1,f2,f3&fields2=f51,f52,f53&klt=101&fqt=1&beg=19900101&end=20500101"),
    ("sina-qfq", "https://finance.sina.com.cn/realstock/company/sh600487/qfq.js"),
    ("sina-hfq", "https://finance.sina.com.cn/realstock/company/sh600487/hfq.js"),
    ("sina-klc", "https://finance.sina.com.cn/realstock/company/sh600487/hisdata/klc_kl.js"),
    ("tx-hfq-1day", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600487,day,2011-12-13,2011-12-19,10,hfq"),
]
for name, url in tests:
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"}, timeout=25)
        print(f"{name:14s} {r.status_code} len={len(r.content):8d} :: {r.text[:160]!r}")
    except Exception as e:
        print(f"{name:14s} ERR {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)
