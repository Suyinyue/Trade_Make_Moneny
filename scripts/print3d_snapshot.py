# -*- coding: utf-8 -*-
"""3D 打印产业链 A 股标的基本面与估值快照。"""
import time
from pathlib import Path

import pandas as pd

RAW = Path(r"E:\Work\MakeMoney\data\raw_3dprint")
RAW.mkdir(parents=True, exist_ok=True)

STOCKS = [
    ("688333", "铂力特", "金属3D打印设备+服务"),
    ("688433", "华曙高科", "金属/高分子3D打印设备"),
    ("002171", "楚江新材", "顶立科技（3D打印设备）"),
    ("300227", "光韵达", "激光/3D打印服务"),
    ("300337", "银邦股份", "金属材料/3D打印粉末"),
    ("688456", "有研粉材", "金属粉末"),
    ("688786", "悦安新材", "羰基铁粉/粉末"),
    ("002008", "大族激光", "激光设备（含3D打印）"),
    ("000988", "华工科技", "激光设备（含3D打印）"),
]

ABSTRACT_CACHE = RAW / "abstract"
ABSTRACT_CACHE.mkdir(exist_ok=True)


def get_abstract(code: str):
    import akshare as ak

    f = ABSTRACT_CACHE / f"{code}.csv"
    if f.exists():
        return pd.read_csv(f)
    for i in range(3):
        try:
            df = ak.stock_financial_abstract(symbol=code)
            df.to_csv(f, index=False, encoding="utf-8-sig")
            return df
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None


def get_daily(code: str):
    import akshare as ak

    f = RAW / f"{code}.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["date"])
    prefix = "sh" if code.startswith("6") else "sz"
    for i in range(3):
        try:
            df = ak.stock_zh_a_daily(symbol=prefix + code, adjust="")
            df.to_csv(f, index=False, encoding="utf-8-sig")
            return pd.read_csv(f, parse_dates=["date"])
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None


rows = []
for code, name, seg in STOCKS:
    ab = get_abstract(code)
    dl = get_daily(code)
    if ab is None or dl is None:
        print("skip", code, name)
        continue
    ser = ab.drop_duplicates(subset="指标", keep="first").set_index("指标")
    col = "20260930"
    if col not in ser.columns:
        print("no 2026Q3", code, name, ser.columns[:4].tolist())
        continue

    def val(ind, c):
        try:
            return float(ser.loc[ind, c])
        except Exception:  # noqa: BLE001
            return float("nan")

    np_26q3 = val("归母净利润", "20260930")
    np_25q3 = val("归母净利润", "20250930")
    np_25fy = val("归母净利润", "20251231")
    rev_26q3 = val("营业总收入", "20260930")
    rev_25q3 = val("营业总收入", "20250930")
    cost_26 = val("营业成本", "20260930")
    ttm = np_25fy - np_25q3 + np_26q3

    dl = dl.sort_values("date")
    last = dl.iloc[-1]
    price = float(last["close"])
    shares = float(last["outstanding_share"])
    mcap = price * shares / 1e8

    q = pd.read_csv(RAW / f"{code}.csv", parse_dates=["date"]).sort_values("date").set_index("date")["close"]
    y = q[q.index >= "2026-01-01"]
    base = q[q.index < "2026-01-01"].iloc[-1]
    rows.append(dict(
        name=name, code=code, seg=seg,
        rev_yi=round(rev_26q3 / 1e8, 2), rev_yoy=round(rev_26q3 / rev_25q3 - 1, 4),
        np_yi=round(np_26q3 / 1e8, 3), np_yoy=round(np_26q3 / np_25q3 - 1, 4) if np_25q3 else float("nan"),
        gm=round(1 - cost_26 / rev_26q3, 4) if rev_26q3 else float("nan"),
        ttm_yi=round(ttm / 1e8, 3), pe_ttm=round(mcap / (ttm / 1e8), 1) if ttm > 0 else float("nan"),
        price=round(price, 2), mcap=round(mcap, 1),
        ytd=round(price / base - 1, 4), peak=round(y.max(), 2), dd=round(price / y.max() - 1, 4),
    ))

print(pd.DataFrame(rows).to_string(index=False))
