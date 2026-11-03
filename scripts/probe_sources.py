import requests, time

tests = [
    ("em-push2his", "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600487&fields1=f1&fields2=f51,f52,f53&klt=101&fqt=0&beg=19900101&end=20500101"),
    ("em-40.push2his", "https://40.push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600487&fields1=f1&fields2=f51,f52,f53&klt=101&fqt=0&beg=19900101&end=20500101"),
    ("em-push2", "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600487&fields=f43,f57,f58"),
    ("tencent-fqkline", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600487,day,1990-01-01,2026-11-01,640,qfq"),
    ("tencent-kline", "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600487,day,1990-01-01,2026-11-01,640"),
    ("sina-hq", "https://hq.sinajs.cn/list=sh600487"),
    ("sina-kline", "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh600487&scale=240&ma=no&datalen=100"),
    ("163-chd", "http://quotes.money.163.com/service/chddata.html?code=0600487&start=19900101&end=20261101&fields=TCLOSE"),
    ("baostock-web", "https://www.baostock.com"),
]
hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
       "Referer": "https://finance.sina.com.cn"}
for name, url in tests:
    for attempt in (1, 2):
        try:
            r = requests.get(url, headers=hdr, timeout=25)
            print(f"{name:18s} {r.status_code} len={len(r.content):8d} :: {r.text[:110]!r}")
            break
        except Exception as e:
            print(f"{name:18s} ERR {type(e).__name__}: {str(e)[:70]}")
            time.sleep(3)
    time.sleep(1)
