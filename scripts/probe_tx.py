import requests, json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
cases = [
    ("raw-url-nohdr", "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600487,day,2003-01-01,2026-11-01,640", None),
    ("raw-url-ua", "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600487,day,2003-01-01,2026-11-01,640", {"User-Agent": UA}),
    ("raw-url-ua-ref", "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600487,day,2003-01-01,2026-11-01,640", {"User-Agent": UA, "Referer": "https://gu.qq.com/sh600487/gp"}),
    ("params-ua", None, {"User-Agent": UA}),
    ("fq-raw-url-ua", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600487,day,2003-01-01,2026-11-01,640,qfq", {"User-Agent": UA}),
]
for name, url, hdr in cases:
    try:
        if url is None:
            r = requests.get("https://web.ifzq.gtimg.cn/appstock/app/kline/kline",
                             params={"param": "sh600487,day,2003-01-01,2026-11-01,640"}, headers=hdr, timeout=25)
        else:
            r = requests.get(url, headers=hdr, timeout=25)
        j = r.json()
        key = list(j.get("data", {}).get("sh600487", {}).keys()) if isinstance(j.get("data"), dict) else None
        print(f"{name:16s} {r.status_code} code={j.get('code')} msg={j.get('msg')!r} keys={key} len={len(r.content)}")
    except Exception as e:
        print(f"{name:16s} ERR {type(e).__name__}: {str(e)[:80]}")
