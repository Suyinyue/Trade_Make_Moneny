# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

RAW = Path(r"E:\Work\MakeMoney\data\raw")
codes = {
    "sh000001": "SHCOMP", "sz399001": "SZCZ", "sh000300": "CSI300",
    "sh000905": "CSI500", "sh000852": "CSI1000", "sz399006": "CHINEXT",
    "sh000688": "STAR50", "bj899050": "BSE50", "sh000016": "SSE50",
    "sh000015": "SSE_DIV",
}
rows = []
for code, name in codes.items():
    df = pd.read_csv(RAW / f"{code}.csv", parse_dates=["date"]).sort_values("date")
    c = df.set_index("date")["close"]
    last = c.iloc[-1]
    y26 = c[c.index >= "2026-01-01"]
    peak26 = y26.max()
    peak_date = y26.idxmax()
    ytd_base = c[c.index < "2026-01-01"].iloc[-1]
    rows.append(dict(
        idx=name, last=round(last, 2), date=str(c.index[-1].date()),
        peak26=round(peak26, 2), peak_date=str(peak_date.date()),
        dd_from_peak=round(last / peak26 - 1, 4),
        r5=round(last / c.iloc[-6] - 1, 4),
        r20=round(last / c.iloc[-21] - 1, 4),
        r60=round(last / c.iloc[-61] - 1, 4),
        ytd=round(last / ytd_base - 1, 4),
        ma20=round(last / c.rolling(20).mean().iloc[-1] - 1, 4),
        ma60=round(last / c.rolling(60).mean().iloc[-1] - 1, 4),
        ma250=round(last / c.rolling(250).mean().iloc[-1] - 1, 4),
    ))
out = pd.DataFrame(rows)
print(out.to_string(index=False))

sh = pd.read_csv(RAW / "sh000001.csv", parse_dates=["date"]).sort_values("date").set_index("date")
print("\n--- SHCOMP last 20 sessions ---")
t = sh.tail(20)[["open", "high", "low", "close", "volume"]].copy()
t["pct"] = (t["close"] / t["close"].shift(1) - 1).round(4)
t["vol_vs_60d"] = (t["volume"] / sh["volume"].rolling(60).mean()).round(2).tail(20)
print(t.to_string())
print("\n--- SHCOMP yearly high/low 2026 ---")
y = sh[sh.index >= "2026-01-01"]
print("high", y["close"].max(), y["close"].idxmax().date(), "low", y["close"].min(), y["close"].idxmin().date())
print("close", sh["close"].iloc[-1], sh.index[-1].date())
print("sessions down of last 20:", int((t["pct"] < 0).sum()), "up:", int((t["pct"] > 0).sum()))
print("avg vol last5 / avg vol prior55:", round(t["volume"].tail(5).mean() / sh["volume"].iloc[-60:-5].mean(), 2))
