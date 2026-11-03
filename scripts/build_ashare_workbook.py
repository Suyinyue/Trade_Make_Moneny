# -*- coding: utf-8 -*-
"""
生成《A股主要指数全历史数据》Excel 工作簿。

数据源：新浪财经（经 AKShare stock_zh_index_daily 接口）
范围：16 个主要指数自各自数据起始日至最新交易日（2026-10-30）的全部日线。
输出：E:\\Work\\MakeMoney\\A股主要指数全历史数据.xlsx
"""
from __future__ import annotations

import datetime as dt
import math
import sys
import time
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

ROOT = Path(r"E:\Work\MakeMoney")
RAW_DIR = ROOT / "data" / "raw"
OUT_FILE = ROOT / "A股主要指数全历史数据.xlsx"

# code, 全称, 简称(工作表名), 备注
INDICES = [
    ("sh000001", "上证综合指数", "上证综指", "上交所全部上市股票，1990-12-19 发布，基点 100"),
    ("sz399001", "深证成份指数", "深证成指", "深市 500 只样本股；新浪数据自 1991-04-03 回溯"),
    ("sz399106", "深证综合指数", "深证综指", "深交所全部上市股票"),
    ("sh000010", "上证180指数", "上证180", "沪市大盘蓝筹代表"),
    ("sh000300", "沪深300指数", "沪深300", "沪深两市 300 只大盘股；新浪数据自 2002-01-04 回溯"),
    ("sh000903", "中证100指数", "中证100", "沪深 100 只超大盘股"),
    ("sh000016", "上证50指数", "上证50", "沪市规模最大、流动性最好的 50 只"),
    ("sh000905", "中证500指数", "中证500", "剔除沪深300后的 500 只中盘股"),
    ("sh000015", "上证红利指数", "上证红利", "沪市高股息率 50 只"),
    ("sz399005", "中小100指数", "中小100", "原中小板指（2006-01-24 发布）；新浪数据自 2008-06-30"),
    ("sz399006", "创业板指数", "创业板指", "创业板 100 只样本股，2010-06-01 基日"),
    ("sz399102", "创业板综合指数", "创业板综", "创业板全部上市股票"),
    ("sh000009", "上证380指数", "上证380", "沪市中小盘成长股 380 只"),
    ("sh000852", "中证1000指数", "中证1000", "小盘股代表；新浪数据自 2014-10-17 回溯"),
    ("sh000688", "科创50指数", "科创50", "科创板 50 只；新浪数据自 2020-01-02 回溯"),
    ("bj899050", "北证50成份指数", "北证50", "北交所 50 只；新浪数据自 2022-05-05 回溯"),
]

MAJOR = ["上证综指", "深证成指", "沪深300", "创业板指"]

# 日期, 事件, 说明
EVENTS = [
    ("1990-12-19", "上海证券交易所开业", "上证综指以 100 点为基点开始发布，A 股市场正式起步"),
    ("1991-07-03", "深圳证券交易所正式开业", "深市进入规范化运作阶段"),
    ("1992-01-19", "邓小平南巡", "市场经济方向确立，股市进入快速扩张期"),
    ("1992-10-12", "中国证监会成立", "统一监管体系建立"),
    ("1996-12-16", "涨跌停板制度实施", "沪深两市个股涨跌幅限制为 ±10%"),
    ("1998-12-29", "《证券法》通过", "1999-07-01 起施行，证券市场进入法治化阶段"),
    ("2001-06-12", "国有股减持办法发布", "市场大幅调整，上证综指随后数月下跌逾 30%"),
    ("2002-06-24", "停止境内减持国有股", "政策转向，当日两市大幅上涨"),
    ("2005-04-08", "沪深300指数发布", "首个跨市场统一指数"),
    ("2005-04-29", "股权分置改革启动", "解决流通股与非流通股分置问题，开启两年大牛市"),
    ("2007-10-16", "上证综指创历史最高", "盘中最高 6124.04 点、收盘 6092.06 点，至今未被超越"),
    ("2008-10-28", "上证综指见底", "盘中最低 1664.93 点，较最高点回撤逾 70%，当日收盘反弹至 1771.82 点"),
    ("2010-03-31", "融资融券试点启动", "A 股进入双向交易时代"),
    ("2010-04-16", "沪深300股指期货上市", "首个场内金融期货品种"),
    ("2014-11-17", "沪港通开通", "内地与香港资本市场互联互通"),
    ("2015-06-12", "杠杆牛顶点", "上证综指盘中 5178.19 点、收盘 5166.35 点，随后发生股灾"),
    ("2016-01-04", "熔断机制实施", "4 个交易日后暂停，熔断制度退出"),
    ("2017-06-21", "A股纳入 MSCI 新兴市场指数", "2018 年 6 月正式纳入"),
    ("2019-07-22", "科创板首批公司上市", "注册制试点启动"),
    ("2020-07-22", "上证综指编制方案修订", "纳入科创板股票，剔除风险警示股"),
    ("2021-11-15", "北京证券交易所开市", "北证50指数成为北交所核心宽基指数"),
    ("2023-02-17", "全面注册制落地", "主板发行审核由核准制改为注册制"),
    ("2024-04-12", "新“国九条”发布", "强化分红、退市与市值管理要求"),
    ("2024-09-24", "一揽子增量政策出台", "市场放量反弹，上证综指单日涨 4.15%"),
]

# ---------- 样式 ----------
FONT_CN = "微软雅黑"
NAVY = "1F4E79"
LIGHT_BLUE = "DCE6F1"
BAND = "F2F7FB"
GREY = "808080"
RED = "C00000"
GREEN = "008000"

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(name=FONT_CN, size=10, bold=True, color="FFFFFF")
TITLE_FONT = Font(name=FONT_CN, size=16, bold=True, color=NAVY)
SUB_FONT = Font(name=FONT_CN, size=10, color=GREY)

NUM2 = "#,##0.00"
NUM4 = "#,##0.0000"
PCT = "0.00%"
PCT1 = "0.0%"
INT = "#,##0"


def header_row(ws, row: int, headers: list[str]) -> None:
    for col, text in enumerate(headers, start=1):
        c = ws.cell(row=row, column=col, value=text)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = 28


def body_style(ws, row: int, ncols: int, band: bool = True) -> None:
    if band and row % 2 == 0:
        fill = PatternFill("solid", fgColor=BAND)
    else:
        fill = None
    for col in range(1, ncols + 1):
        c = ws.cell(row=row, column=col)
        c.font = Font(name=FONT_CN, size=9)
        c.border = BORDER
        if fill is not None:
            c.fill = fill


def set_widths(ws, widths: list[float]) -> None:
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def setup_print(ws, landscape: bool = True, titles: str | None = None,
                area: str | None = None, fit_height: int = 0, bottom: float = 0.5) -> None:
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = fit_height
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = bottom
    if titles:
        ws.print_title_rows = titles
    if area:
        ws.print_area = area
    ws.oddFooter.center.text = "第 &P 页 / 共 &N 页"


def pct_change_color(ws, cell_range: str) -> None:
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT_CN, size=9, color=RED))
    )
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="lessThan", formula=["0"], font=Font(name=FONT_CN, size=9, color=GREEN))
    )


# ---------- 取数 ----------
def fetch(code: str) -> pd.DataFrame:
    import akshare as ak

    cache = RAW_DIR / f"{code}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(4):
        try:
            df = ak.stock_zh_index_daily(symbol=code)
            df.to_csv(cache, index=False, encoding="utf-8-sig")
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{code} 取数失败: {last_err}")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).drop_duplicates(subset=["date"]).sort_values("date")
    df = df.reset_index(drop=True)
    df["pct"] = df["close"].pct_change()
    df["chg"] = df["close"].diff()
    df["amp"] = (df["high"] - df["low"]) / df["close"].shift(1)
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    df["ma250"] = df["close"].rolling(250).mean()
    return df


def metrics(df: pd.DataFrame) -> dict:
    first, last = df.iloc[0], df.iloc[-1]
    n = len(df)
    days = (last["date"] - first["date"]).days
    total = last["close"] / first["close"] - 1
    cagr = (last["close"] / first["close"]) ** (365.25 / days) - 1 if days > 0 else float("nan")
    vol = df["pct"].std(ddof=1) * math.sqrt(252)
    cummax = df["close"].cummax()
    dd = df["close"] / cummax - 1
    trough_i = int(dd.idxmin())
    peak_i = int(df["close"].iloc[: trough_i + 1].idxmax())
    hi_i = int(df["close"].idxmax())
    lo_i = int(df["close"].idxmin())
    yearly = df.groupby(df["date"].dt.year)["close"].last()
    yearly_ret = yearly.pct_change()
    yearly_ret.iloc[0] = yearly.iloc[0] / df.iloc[0]["close"] - 1
    return dict(
        start=first["date"], end=last["date"], n=n,
        first_close=first["close"], last_close=last["close"],
        total=total, cagr=cagr, vol=vol,
        mdd=float(dd.min()), peak_date=df.loc[peak_i, "date"], trough_date=df.loc[trough_i, "date"],
        high=float(df.loc[hi_i, "close"]), high_date=df.loc[hi_i, "date"],
        low=float(df.loc[lo_i, "close"]), low_date=df.loc[lo_i, "date"],
        up_years=int((yearly_ret > 0).sum()), total_years=int(len(yearly_ret)),
        avg_volume=float(df["volume"].mean()),
        zero_vol=int(((df["volume"] == 0) | df["volume"].isna()).sum()),
    )


# ---------- 工作表 ----------
def sheet_readme(wb: Workbook, data: dict, generated: dt.datetime) -> None:
    ws = wb.create_sheet("说明")
    ws.sheet_view.showGridLines = False
    set_widths(ws, [3, 18, 96])

    ws.merge_cells("B2:C2")
    c = ws["B2"]
    c.value = "A 股主要指数全历史数据"
    c.font = TITLE_FONT
    ws.row_dimensions[2].height = 30

    ws.merge_cells("B3:C3")
    c = ws["B3"]
    c.value = "自 1990 年 12 月 19 日上证综指开盘起，至最新交易日 2026 年 10 月 30 日"
    c.font = SUB_FONT

    rows = [
        ("一、文件构成", ""),
        ("指数概览", "16 个指数的覆盖区间、累计收益、年化收益、波动率、最大回撤、历史极值等汇总指标"),
        ("最新行情", "截至 2026-10-30 的各指数收盘、日涨跌、近 5/20/60 日、年初至今、近一年表现"),
        ("年度涨跌幅", "1990—2026 年各指数逐年涨跌幅矩阵，红色为上涨、绿色为下跌"),
        ("上证综指年度统计", "上证综指逐年开高低收、涨跌幅、振幅与成交量"),
        ("走势图", "四大宽基指数自 2010-06-01 起归一化（基点=100）的走势对比图；底层数据见「归一化数据」"),
        ("各指数明细", "每个指数一张工作表：日期、开高低收、成交量、涨跌额、涨跌幅、振幅、MA20/60/250，并附收盘价走势图"),
        ("大事记", "A 股市场重大制度与行情节点，附当日上证综指收盘点位"),
        ("", ""),
        ("二、数据口径", ""),
        ("数据来源", "新浪财经日线行情，经 AKShare 1.17.87 的 stock_zh_index_daily 接口获取"),
        ("时间范围", "各指数自新浪可回溯的最早交易日至 2026-10-30，覆盖 36 个自然年"),
        ("复权方式", "指数点位为价格指数，不含分红再投资，无复权处理"),
        ("价格单位", "点（指数点位），保留原始精度；表中统一保留两位小数显示"),
        ("成交量单位", "股；为该指数成分股当日成交股数合计，不含成交金额"),
        ("涨跌幅", "由收盘价计算：(当日收盘 / 前一日收盘 - 1)，首行为空"),
        ("振幅", "（当日最高 - 当日最低）/ 前一日收盘"),
        ("年化收益", "按自然日复合年化：(末值 / 初值) ^ (365.25 / 天数) - 1"),
        ("年化波动率", "日收益率标准差 × √252"),
        ("最大回撤", "收盘价相对历史最高收盘的最大跌幅，并给出回撤起点与低点日期"),
        ("", ""),
        ("三、注意事项", ""),
        ("回溯数据", "沪深300、中证500/1000、创业板指、科创50、北证50 等指数的新浪数据早于其正式发布日期，属于指数公司按基日回溯计算的历史点位，用于连续性研究，不等同于当时可交易的实时行情"),
        ("样本调整", "指数成分股定期调整，历史点位为按现行规则回溯的结果，与当年的实际成分并不完全一致"),
        ("停牌与零成交", "早期数据存在成交量为 0 的记录，已在各指数明细中原样保留"),
        ("更新方式", "重新运行 scripts/build_ashare_workbook.py 可增量更新；删除 data/raw 目录可强制重新抓取"),
        ("免责声明", "本文件仅供研究与学习使用，不构成任何投资建议；数据以交易所及指数公司官方披露为准"),
        ("", ""),
        ("生成时间", generated.strftime("%Y-%m-%d %H:%M:%S")),
    ]

    r = 5
    for key, val in rows:
        if val == "" and key:
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
            c = ws.cell(row=r, column=2, value=key)
            c.font = Font(name=FONT_CN, size=11, bold=True, color=NAVY)
            c.fill = PatternFill("solid", fgColor=LIGHT_BLUE)
            c.alignment = Alignment(vertical="center")
            ws.row_dimensions[r].height = 22
        elif key == "":
            ws.row_dimensions[r].height = 8
        else:
            k = ws.cell(row=r, column=2, value=key)
            k.font = Font(name=FONT_CN, size=10, bold=True)
            k.alignment = Alignment(vertical="top")
            v = ws.cell(row=r, column=3, value=val)
            v.font = Font(name=FONT_CN, size=10)
            v.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = max(18, 15 * (len(str(val)) // 60 + 1))
        r += 1
    setup_print(ws, landscape=False, area=f"A1:C{r - 1}")


def sheet_overview(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("指数概览")
    ws.sheet_view.showGridLines = False
    headers = [
        "序号", "指数名称", "代码", "数据起始", "数据截止", "交易日数",
        "起始收盘", "最新收盘", "累计涨跌幅", "年化收益", "年化波动率",
        "最大回撤", "回撤起点", "回撤低点", "历史最高收盘", "最高日期",
        "历史最低收盘", "最低日期", "上涨年份/总年份", "日均成交量(亿股)", "备注",
    ]
    header_row(ws, 1, headers)

    r = 2
    for i, (code, full, short, note) in enumerate(INDICES, start=1):
        m = data[code]["metrics"]
        remark = note
        if m["zero_vol"]:
            remark += f"；回溯期零成交 {m['zero_vol']} 个交易日"
        vals = [
            i, full, code, m["start"].to_pydatetime(), m["end"].to_pydatetime(), m["n"],
            m["first_close"], m["last_close"], m["total"], m["cagr"], m["vol"],
            m["mdd"], m["peak_date"].to_pydatetime(), m["trough_date"].to_pydatetime(),
            m["high"], m["high_date"].to_pydatetime(), m["low"], m["low_date"].to_pydatetime(),
            f"{m['up_years']}/{m['total_years']}", m["avg_volume"] / 1e8, remark,
        ]
        for col, v in enumerate(vals, start=1):
            ws.cell(row=r, column=col, value=v)
        body_style(ws, r, len(headers))
        for col in (4, 5, 13, 14, 16, 18):
            ws.cell(row=r, column=col).number_format = "yyyy-mm-dd"
        for col in (7, 8, 15, 17):
            ws.cell(row=r, column=col).number_format = NUM2
        for col in (9, 10, 11, 12):
            ws.cell(row=r, column=col).number_format = PCT
        ws.cell(row=r, column=20).number_format = "#,##0.00"
        ws.row_dimensions[r].height = 30
        r += 1

    pct_change_color(ws, f"I2:K{r - 1}")
    set_widths(ws, [5, 18, 10, 11, 11, 9, 11, 11, 11, 10, 10, 10, 11, 11, 12, 11, 12, 11, 13, 14, 46])
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:U{r - 1}"
    ws.row_dimensions[1].height = 34
    for row in ws.iter_rows(min_row=2, max_row=r - 1, min_col=21, max_col=21):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
    ws.row_dimensions[r].height = 8
    setup_print(ws, area=f"A1:U{r - 1}")


def sheet_latest(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("最新行情")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:N1")
    c = ws["A1"]
    c.value = "各指数最新行情（2026-10-30 收盘）"
    c.font = TITLE_FONT
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26

    headers = [
        "指数名称", "代码", "最新交易日", "收盘", "涨跌额", "涨跌幅",
        "近5日", "近20日", "近60日", "年初至今", "近一年",
        "历史最高收盘", "最高日期", "距历史最高",
    ]
    header_row(ws, 3, headers)

    r = 4
    for code, full, short, _ in INDICES:
        df = data[code]["df"]
        m = data[code]["metrics"]
        last = df.iloc[-1]

        def ret(n: int):
            if len(df) <= n:
                return None
            return df["close"].iloc[-1] / df["close"].iloc[-1 - n] - 1

        ytd_base = df[df["date"] < pd.Timestamp("2026-01-01")]
        ytd = last["close"] / ytd_base["close"].iloc[-1] - 1 if len(ytd_base) else None
        y1 = ret(250)

        vals = [
            full, code, last["date"].to_pydatetime(), last["close"], last["chg"], last["pct"],
            ret(5), ret(20), ret(60), ytd, y1,
            m["high"], m["high_date"].to_pydatetime(), last["close"] / m["high"] - 1,
        ]
        for col, v in enumerate(vals, start=1):
            ws.cell(row=r, column=col, value=v)
        body_style(ws, r, len(headers))
        ws.cell(row=r, column=3).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=13).number_format = "yyyy-mm-dd"
        for col in (4, 5, 12):
            ws.cell(row=r, column=col).number_format = NUM2
        for col in (6, 7, 8, 9, 10, 11, 14):
            ws.cell(row=r, column=col).number_format = PCT
        r += 1

    pct_change_color(ws, f"F4:K{r - 1}")
    pct_change_color(ws, f"N4:N{r - 1}")
    set_widths(ws, [20, 10, 11, 11, 9, 9, 9, 9, 9, 10, 9, 12, 11, 10])
    ws.freeze_panes = "C4"
    setup_print(ws, area=f"A1:N{r - 1}")


def sheet_annual(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("年度涨跌幅")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:Q1")
    c = ws["A1"]
    c.value = "各指数年度涨跌幅（单位：%）"
    c.font = TITLE_FONT
    ws.row_dimensions[1].height = 26

    headers = ["年份"] + [short for _, _, short, _ in INDICES]
    header_row(ws, 3, headers)

    # 计算各指数年度涨跌幅
    years = list(range(1990, 2027))
    table = {}
    for code, _, short, _ in INDICES:
        df = data[code]["df"]
        y_last = df.groupby(df["date"].dt.year)["close"].last()
        y_ret = y_last.pct_change()
        first_year = y_last.index.min()
        y_ret.loc[first_year] = y_last.loc[first_year] / df.iloc[0]["close"] - 1
        table[short] = y_ret

    r = 4
    for y in years:
        ws.cell(row=r, column=1, value=y)
        for col, (_, _, short, _) in enumerate(INDICES, start=2):
            v = table[short].get(y)
            if v is not None and not pd.isna(v):
                ws.cell(row=r, column=col, value=float(v))
        body_style(ws, r, len(headers))
        ws.cell(row=r, column=1).alignment = Alignment(horizontal="center")
        for col in range(2, len(headers) + 1):
            ws.cell(row=r, column=col).number_format = PCT1
        r += 1

    pct_change_color(ws, f"B4:Q{r - 1}")
    note = ws.cell(row=r + 1, column=1,
                   value="注：首年涨跌幅以该指数数据首日收盘为基期；空白表示该指数当年尚未开始发布。红色为上涨，绿色为下跌。")
    note.font = SUB_FONT
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=len(headers))
    note.alignment = Alignment(vertical="center")
    set_widths(ws, [8] + [11] * len(INDICES))
    ws.freeze_panes = "B4"
    setup_print(ws, area=f"A1:Q{r + 1}")


def sheet_sh_year(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("上证综指年度统计")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:H1")
    ws["A1"].value = "上证综指逐年统计"
    ws["A1"].font = TITLE_FONT
    ws.row_dimensions[1].height = 26

    headers = ["年份", "开盘", "最高", "最低", "收盘", "年度涨跌幅", "振幅", "成交量(亿股)"]
    header_row(ws, 3, headers)

    df = data["sh000001"]["df"]
    r = 4
    for year, g in df.groupby(df["date"].dt.year):
        prev_close = df[df["date"] < pd.Timestamp(year=year, month=1, day=1)]["close"]
        base = prev_close.iloc[-1] if len(prev_close) else g["close"].iloc[0]
        ret = g["close"].iloc[-1] / base - 1
        amp = g["high"].max() / g["low"].min() - 1
        vals = [int(year), g["open"].iloc[0], g["high"].max(), g["low"].min(),
                g["close"].iloc[-1], ret, amp, g["volume"].sum() / 1e8]
        for col, v in enumerate(vals, start=1):
            ws.cell(row=r, column=col, value=v)
        body_style(ws, r, len(headers))
        for col in (2, 3, 4, 5):
            ws.cell(row=r, column=col).number_format = NUM2
        for col in (6, 7):
            ws.cell(row=r, column=col).number_format = PCT
        ws.cell(row=r, column=8).number_format = "#,##0.00"
        r += 1

    pct_change_color(ws, f"F4:G{r - 1}")
    note = ws.cell(row=r + 1, column=1,
                   value="注：涨跌幅以上一年度最后一个交易日收盘为基期，首年以数据首日收盘为基期；"
                         "振幅 = (年内最高 - 年内最低) / 上年收盘；成交量单位为亿股。")
    note.font = SUB_FONT
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=len(headers))
    note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r + 1].height = 28
    set_widths(ws, [8, 12, 12, 12, 12, 13, 12, 16])
    ws.freeze_panes = "B4"
    ws.auto_filter.ref = f"A3:H{r - 1}"
    setup_print(ws, area=f"A1:H{r + 1}", fit_height=1, bottom=0.9)


def sheet_trend(wb: Workbook, data: dict) -> None:
    base_date = pd.Timestamp("2010-06-01")
    series = {}
    for short in MAJOR:
        code = next(c for c, _, s, _ in INDICES if s == short)
        df = data[code]["df"]
        d = df[df["date"] >= base_date][["date", "close"]].copy()
        d["norm"] = d["close"] / d["close"].iloc[0] * 100
        series[short] = d.set_index("date")["norm"]
    frame = pd.DataFrame(series).sort_index()

    # ---- 图表页 ----
    ws = wb.create_sheet("走势图")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "四大宽基指数归一化走势（2010-06-01 = 100）"
    ws["A1"].font = TITLE_FONT
    ws.row_dimensions[1].height = 28
    ws["A2"] = "以 2010-06-01 首个交易日收盘为 100 归一化；底层数据见「归一化数据」工作表"
    ws["A2"].font = SUB_FONT

    chart = LineChart()
    chart.title = "四大宽基指数归一化走势（2010-06-01 = 100）"
    chart.style = 2
    chart.height = 16
    chart.width = 32
    chart.y_axis.title = "归一化点位"
    chart.x_axis.title = "日期"
    chart.x_axis.number_format = "yyyy"
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.legend.position = "b"
    ws.add_chart(chart, "A4")
    setup_print(ws, area="A1:R38")

    # ---- 数据页 ----
    ws_data = wb.create_sheet("归一化数据")
    ws_data.sheet_view.showGridLines = False
    ws_data["A1"] = "四大宽基指数归一化数据（2010-06-01 = 100）"
    ws_data["A1"].font = TITLE_FONT
    ws_data.row_dimensions[1].height = 26
    header = ["日期"] + MAJOR
    for col, h in enumerate(header, start=1):
        c = ws_data.cell(row=4, column=col, value=h)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center")

    r = 5
    for date, row in frame.iterrows():
        ws_data.cell(row=r, column=1, value=date.to_pydatetime()).number_format = "yyyy-mm-dd"
        for col, short in enumerate(MAJOR, start=2):
            v = row.get(short)
            if pd.notna(v):
                ws_data.cell(row=r, column=col, value=float(v)).number_format = NUM2
        r += 1

    ws_data.column_dimensions["A"].width = 12
    for col in range(2, 6):
        ws_data.column_dimensions[get_column_letter(col)].width = 14
    setup_print(ws_data, titles="4:4", area=f"A1:E{r - 1}")

    # 补齐图表数据源
    data_ref = Reference(ws_data, min_col=2, max_col=5, min_row=4, max_row=r - 1)
    cats = Reference(ws_data, min_col=1, min_row=5, max_row=r - 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats)
    colors = {"上证综指": "1F4E79", "深证成指": "ED7D31", "沪深300": "C00000", "创业板指": "2E7D32"}
    for s, short in zip(chart.series, MAJOR):
        s.smooth = False
        s.graphicalProperties.line.solidFill = colors[short]
        s.graphicalProperties.line.width = 15000


def sheet_detail(wb: Workbook, code: str, full: str, short: str, df: pd.DataFrame) -> None:
    ws = wb.create_sheet(short[:31])
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value = f"{full}（{code}）全部历史日线"
    c.font = TITLE_FONT
    ws.row_dimensions[1].height = 24

    note = ws.cell(row=2, column=1, value=f"{df['date'].iloc[0]:%Y-%m-%d} 至 {df['date'].iloc[-1]:%Y-%m-%d}，共 {len(df):,} 个交易日")
    note.font = SUB_FONT

    headers = ["日期", "开盘", "最高", "最低", "收盘", "成交量(股)", "涨跌额", "涨跌幅", "振幅", "MA20", "MA60", "MA250"]
    header_row(ws, 4, headers)

    r = 5
    for row in df.itertuples(index=False):
        ws.cell(row=r, column=1, value=row.date.to_pydatetime()).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=2, value=float(row.open)).number_format = NUM2
        ws.cell(row=r, column=3, value=float(row.high)).number_format = NUM2
        ws.cell(row=r, column=4, value=float(row.low)).number_format = NUM2
        ws.cell(row=r, column=5, value=float(row.close)).number_format = NUM2
        ws.cell(row=r, column=6, value=int(row.volume) if pd.notna(row.volume) else None).number_format = INT
        if pd.notna(row.chg):
            ws.cell(row=r, column=7, value=float(row.chg)).number_format = NUM2
        if pd.notna(row.pct):
            ws.cell(row=r, column=8, value=float(row.pct)).number_format = PCT
        if pd.notna(row.amp):
            ws.cell(row=r, column=9, value=float(row.amp)).number_format = PCT
        for col, v in ((10, row.ma20), (11, row.ma60), (12, row.ma250)):
            if pd.notna(v):
                ws.cell(row=r, column=col, value=float(v)).number_format = NUM2
        body_style(ws, r, len(headers))
        r += 1

    set_widths(ws, [12, 11, 11, 11, 11, 16, 10, 9, 9, 11, 11, 11])
    ws.freeze_panes = "B5"
    ws.auto_filter.ref = f"A4:L{r - 1}"
    setup_print(ws, titles="4:4", area=f"A1:L{r - 1}")

    chart = LineChart()
    chart.title = f"{full} 收盘价走势"
    chart.style = 2
    chart.height = 9
    chart.width = 20
    chart.y_axis.title = "点"
    chart.x_axis.number_format = "yyyy"
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.legend.position = "b"
    data_ref = Reference(ws, min_col=5, min_row=4, max_row=r - 1)
    cats = Reference(ws, min_col=1, min_row=5, max_row=r - 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats)
    for s in chart.series:
        s.smooth = False
        s.graphicalProperties.line.solidFill = NAVY
        s.graphicalProperties.line.width = 14000
    ws.add_chart(chart, "N4")


def sheet_events(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("大事记")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:E1")
    ws["A1"].value = "A 股市场大事记（附当日上证综指）"
    ws["A1"].font = TITLE_FONT
    ws.row_dimensions[1].height = 26

    headers = ["日期", "事件", "说明", "上证综指收盘", "距今天数"]
    header_row(ws, 3, headers)

    sh = data["sh000001"]["df"].set_index("date")
    last_date = sh.index[-1]
    r = 4
    for date_str, event, desc in EVENTS:
        d = pd.Timestamp(date_str)
        eligible = sh[sh.index <= d]
        row_date = eligible.index[-1] if len(eligible) else None
        close = float(eligible["close"].iloc[-1]) if len(eligible) else None
        ws.cell(row=r, column=1, value=pd.Timestamp(date_str).to_pydatetime()).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=2, value=event)
        ws.cell(row=r, column=3, value=desc)
        if close is not None:
            ws.cell(row=r, column=4, value=close).number_format = NUM2
            ws.cell(row=r, column=5, value=(last_date - row_date).days).number_format = INT
        body_style(ws, r, len(headers))
        ws.cell(row=r, column=3).alignment = Alignment(wrap_text=True, vertical="center")
        r += 1

    set_widths(ws, [12, 30, 70, 14, 10])
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:E{r - 1}"
    setup_print(ws, area=f"A1:E{r - 1}")


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    for code, full, short, note in INDICES:
        df_raw = fetch(code)
        df = clean(df_raw)
        data[code] = {"df": df, "metrics": metrics(df), "note": note}
        m = data[code]["metrics"]
        print(f"[OK] {code} {short}: {m['n']} 行, {m['start']:%Y-%m-%d} ~ {m['end']:%Y-%m-%d}, "
              f"累计 {m['total']:.2%}, 零成交 {m['zero_vol']}")

    generated = dt.datetime.now()
    wb = Workbook()
    wb.remove(wb.active)

    sheet_readme(wb, data, generated)
    sheet_overview(wb, data)
    sheet_latest(wb, data)
    sheet_annual(wb, data)
    sheet_sh_year(wb, data)
    sheet_trend(wb, data)
    for code, full, short, _ in INDICES:
        sheet_detail(wb, code, full, short, data[code]["df"])
    sheet_events(wb, data)

    wb.properties.title = "A股主要指数全历史数据"
    wb.properties.subject = "1990-12-19 至 2026-10-30"
    wb.properties.creator = "AKShare 数据整理"
    wb.properties.description = "数据来源：新浪财经，经 AKShare 获取，仅供研究使用"

    wb.save(OUT_FILE)
    print(f"\n已生成: {OUT_FILE}  ({OUT_FILE.stat().st_size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
