# -*- coding: utf-8 -*-
"""抓取新闻页面正文, 输出为文本便于整理"""
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")}
OUT = Path("E:/Work/MakeMoney/data/news")
OUT.mkdir(parents=True, exist_ok=True)

urls = sys.argv[1:]

for i, url in enumerate(urls, 1):
    name = re.sub(r"[^a-zA-Z0-9]+", "_", url)[-60:]
    try:
        r = requests.get(url, headers=UA, timeout=25)
        enc = r.apparent_encoding or "utf-8"
        r.encoding = enc
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else ""
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
        text = re.sub(r"\n{3,}", "\n\n", text)
        path = OUT / f"{i:02d}_{name}.txt"
        path.write_text(f"URL: {url}\nTITLE: {title}\nSTATUS: {r.status_code}\n\n{text}",
                        encoding="utf-8")
        print(f"[{i}] {r.status_code} {len(text):6d} chars  {title[:50]}")
    except Exception as e:
        print(f"[{i}] ERR {type(e).__name__}: {str(e)[:90]}  {url}")
