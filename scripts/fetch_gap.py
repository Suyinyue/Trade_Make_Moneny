# -*- coding: utf-8 -*-
"""补抓 2007-09-04 一根缺失的不复权K线"""
import requests, json

r = requests.get("https://web.ifzq.gtimg.cn/appstock/app/kline/kline",
                 params={"param": "sh600487,day,2007-08-28,2007-09-10,20"}, timeout=20)
rows = r.json()["data"]["sh600487"]["day"]
for row in rows:
    print(row)
