import requests

hosts = [
    "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600487&fields1=f1,f2,f3&fields2=f51,f52&klt=101&fqt=0&beg=19900101&end=20500101",
    "http://quotes.money.163.com/service/chddata.html?code=0600487&start=19900101&end=20261101&fields=TCLOSE",
    "https://www.baidu.com",
    "https://query1.finance.yahoo.com/v8/finance/chart/600487.SS?range=1y&interval=1d",
]
for h in hosts:
    try:
        r = requests.get(h, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        print(h[:70], "->", r.status_code, len(r.content))
    except Exception as e:
        print(h[:70], "-> ERR", type(e).__name__, str(e)[:100])
