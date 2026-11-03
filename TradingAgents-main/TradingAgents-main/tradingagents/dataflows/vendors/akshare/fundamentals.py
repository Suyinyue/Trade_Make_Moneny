"""A-share company fundamentals from akshare.

The profile and the ratios come from Sina and Eastmoney endpoints; the three
statements come from Sina's financial-report endpoint, which serves every
reporting period of a company without an announcement date. Because no A-share
endpoint here says *when* a figure became public, a run dated before today is
served the same point-in-time notice the Yahoo vendor serves rather than figures
that may not have been filed yet — the same integrity rule, applied to a market
that has no SEC EDGAR equivalent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import pandas as pd

from tradingagents.dataflows.date_window import (
    withhold_live_profile,
    withhold_undated_statements,
)
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.vendors.akshare.common import AShareSymbol, ak_retry, resolve

# The ratios worth putting in front of the analyst, matched against Sina's
# column names by substring (the exact spelling drifts between releases).
_KEY_INDICATORS = (
    "摊薄每股收益",
    "每股净资产",
    "净资产收益率",
    "总资产利润率",
    "销售毛利率",
    "销售净利率",
    "资产负债率",
    "流动比率",
    "速动比率",
    "主营业务收入增长率",
    "净利润增长率",
    "总资产增长率",
    "存货周转率",
    "应收账款周转率",
    "经营现金净流量对销售收入比率",
)

_PROFILE_LABELS = {
    # cninfo's company profile
    "公司名称": "Name",
    "A股简称": "Short Name",
    "所属行业": "Industry",
    "所属市场": "Market",
    "上市日期": "Listing Date",
    "主营业务": "Main Business",
    "经营范围": "Business Scope",
    "法人代表": "Legal Representative",
    "注册资金": "Registered Capital",
    # Eastmoney's / Xueqiu's item-value profile
    "股票简称": "Name",
    "股票代码": "Code",
    "行业": "Industry",
    "上市时间": "Listing Date",
    "总市值": "Market Cap (CNY)",
    "流通市值": "Float Market Cap (CNY)",
    "总股本": "Shares Outstanding",
    "流通股": "Float Shares",
}


def _as_frame(func, **kwargs) -> pd.DataFrame | None:
    try:
        frame = ak_retry(lambda: func(**kwargs))
    except VendorUnavailableError:
        return None
    return frame if isinstance(frame, pd.DataFrame) and not frame.empty else None


def _profile(sym: AShareSymbol) -> dict:
    """Company profile as a label->value dict from whichever endpoint answers.

    cninfo answers reliably and carries the business description; the Eastmoney
    and Xueqiu profiles are item/value frames kept as fallbacks because their
    endpoints intermittently return a non-JSON body.
    """
    import akshare as ak

    cninfo = getattr(ak, "stock_profile_cninfo", None)
    if cninfo is not None:
        frame = _as_frame(cninfo, symbol=sym.code)
        if frame is not None:
            row = frame.iloc[0]
            pairs = {
                str(label).strip(): value
                for label, value in row.items()
                if pd.notna(value) and str(value).strip()
            }
            if pairs:
                return pairs

    for name, kwargs in (
        ("stock_individual_info_em", {"symbol": sym.code}),
        ("stock_individual_basic_info_xq", {"symbol": f"{sym.exchange.upper()}{sym.code}"}),
    ):
        fetch = getattr(ak, name, None)
        if fetch is None:
            continue
        frame = _as_frame(fetch, **kwargs)
        if frame is None or not {"item", "value"}.issubset(frame.columns):
            continue
        pairs = {
            str(row["item"]).strip(): row["value"]
            for _, row in frame.iterrows()
        }
        if pairs:
            return pairs
    return {}


def _latest_indicators(sym: AShareSymbol) -> tuple[str, list[str]]:
    """The most recent period's key ratios, as (report date, "label: value" lines)."""
    import akshare as ak

    fetch = getattr(ak, "stock_financial_analysis_indicator", None)
    if fetch is None:
        return "", []
    start_year = str(datetime.now().year - 3)
    frame = _as_frame(fetch, symbol=sym.code, start_year=start_year)
    if frame is None:
        return "", []

    date_col = next((c for c in ("日期", "报告期", "REPORT_DATE") if c in frame.columns), None)
    if date_col is None:
        return "", []
    frame = frame.sort_values(date_col)
    latest = frame.iloc[-1]

    lines = []
    for wanted in _KEY_INDICATORS:
        column = next((c for c in frame.columns if wanted in str(c)), None)
        if column is None:
            continue
        value = latest[column]
        if pd.isna(value):
            continue
        lines.append(f"{column}: {value}")
    return str(latest[date_col]), lines


def get_fundamentals_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    as_of_date: Annotated[str, "analysis date in YYYY-MM-DD format"] = None,
):
    """Profile, valuation and the latest key ratios for an A-share company."""
    sym = resolve(ticker)
    if sym.kind != "stock":
        raise NoMarketDataError(ticker, sym.yahoo, f"no company fundamentals for a {sym.kind}")

    withheld = withhold_live_profile(as_of_date, sym.yahoo)
    if withheld:
        return withheld

    profile = _profile(sym)
    report_date, indicators = _latest_indicators(sym)
    if not profile and not indicators:
        raise VendorUnavailableError(f"no A-share fundamentals endpoint answered for {sym.yahoo}")

    lines = [f"# Company Fundamentals for {sym.yahoo} (akshare)"]
    for item, value in profile.items():
        label = _PROFILE_LABELS.get(item)
        if label is None:
            continue    # the profile frame carries long legal text we do not need
        text = str(value).strip().replace("\n", " ")
        lines.append(f"{label}: {text[:400]}")

    if indicators:
        lines += ["", f"## Key ratios, report period {report_date}", ""]
        lines += indicators

    lines += [
        "",
        "Prices and volumes come from the market-data tools; the figures above are "
        "as of the report period named, in CNY unless the label says otherwise.",
    ]
    return "\n".join(lines)


# Sina returns every line item, 147 columns wide. That is noise in a prompt and
# thousands of tokens per statement, so each statement keeps the lines an
# analyst actually reads, plus the filing date. An unrecognized frame (a vendor
# that spells the columns differently) is passed through untouched.
_STATEMENT_KEY_ITEMS = {
    "Balance Sheet": (
        "货币资金", "应收账款", "存货", "流动资产合计", "固定资产净额", "资产总计",
        "短期借款", "应付账款", "合同负债", "流动负债合计", "长期借款", "负债合计",
        "归属于母公司股东权益合计", "所有者权益(或股东权益)合计",
    ),
    "Income Statement": (
        "营业总收入", "营业收入", "营业总成本", "营业成本", "销售费用", "管理费用",
        "研发费用", "财务费用", "营业利润", "利润总额", "净利润",
        "归属于母公司所有者的净利润",
    ),
    "Cash Flow": (
        "经营活动产生的现金流量净额", "投资活动产生的现金流量净额",
        "筹资活动产生的现金流量净额", "现金及现金等价物净增加额",
    ),
}

_IDENTITY_FIELDS = (
    ("公司名称", "longName"),
    ("A股简称", "shortName"),
    ("所属行业", "industry"),
    ("所属市场", "exchange"),
)


def get_company_profile_akshare(ticker: str) -> dict:
    """Identity fields for an A-share ticker, named like the Yahoo profile's.

    Called before the agents run, so an A-share run does not spend a Yahoo
    request (and its rate limit) resolving a name cninfo already serves.
    Raises for a non-A-share symbol, and the caller falls back to Yahoo.
    """
    sym = resolve(ticker)
    if sym.kind != "stock":
        raise NoMarketDataError(ticker, sym.yahoo, f"no company profile for a {sym.kind}")

    profile = _profile(sym)
    identity = {
        target: str(profile[source])
        for source, target in _IDENTITY_FIELDS
        if profile.get(source)
    }
    if not identity:
        raise VendorUnavailableError(f"no A-share profile answered for {sym.yahoo}")
    return identity


def _statement_frame(sym: AShareSymbol, freq: str, sina_name: str, em_name: str):
    """A statement from Sina, else Eastmoney, as a DataFrame."""
    import akshare as ak

    sina = getattr(ak, "stock_financial_report_sina", None)
    if sina is not None:
        frame = _as_frame(sina, stock=sym.ak, symbol=sina_name)
        if frame is not None:
            return frame

    em = getattr(ak, em_name, None)
    if em is not None:
        return _as_frame(em, symbol=f"{sym.exchange.upper()}{sym.code}")
    return None


def _statement(
    ticker: str,
    freq: str,
    as_of_date: str | None,
    title: str,
    sina_name: str,
    em_name: str,
) -> str:
    sym = resolve(ticker)
    if sym.kind != "stock":
        raise NoMarketDataError(ticker, sym.yahoo, f"no statements for a {sym.kind}")

    frame = _statement_frame(sym, freq, sina_name, em_name)
    if frame is None:
        raise NoMarketDataError(ticker, sym.yahoo, f"no {title.lower()} rows")

    frame = frame.copy()

    # Sina dates each row by the period it covers AND by the day it was filed
    # (公告日期), so a past run can read the statement exactly as filed: a
    # figure restated later still reads as first reported, and a statement not
    # yet announced is not served. A vendor without that column cannot make the
    # claim, so a historical run is told why rather than served anyway.
    notice_col = next((c for c in ("公告日期", "NOTICE_DATE", "公告日") if c in frame.columns), None)
    if notice_col is not None:
        notices = pd.to_datetime(frame[notice_col], errors="coerce")
        cutoff = pd.to_datetime(as_of_date).normalize() if as_of_date else pd.Timestamp.today().normalize()
        frame = frame[notices.notna() & (notices <= cutoff)]
        if frame.empty:
            raise NoMarketDataError(
                ticker, sym.yahoo, f"no {title.lower()} filed on or before {as_of_date}"
            )
    else:
        withheld = withhold_undated_statements(as_of_date, sym.yahoo, title)
        if withheld:
            return withheld

    # Keep the latest few periods, honoring the requested frequency.
    date_col = next((c for c in ("报告日", "REPORT_DATE", "报告期") if c in frame.columns), None)
    if date_col is not None:
        frame["_period"] = frame[date_col].astype(str)
        if freq.lower() == "annual":
            annual = frame[frame["_period"].str.replace("-", "").str[4:8] == "1231"]
            frame = annual if not annual.empty else frame
        frame = frame.sort_values("_period").tail(4).drop(columns=["_period"])

    # Trim to the line items an analyst reads: a 147-column table is noise and
    # thousands of tokens per statement.
    keys = _STATEMENT_KEY_ITEMS.get(title, ())
    matched = [k for k in keys if k in frame.columns]
    if matched:
        wanted = {*matched, date_col, notice_col, "币种"}
        frame = frame[[c for c in frame.columns if c in wanted]]

    return f"# {title} data for {sym.yahoo} ({freq}, akshare)\n" + frame.to_csv(index=False)


def get_balance_sheet_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    as_of_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Balance sheet, latest periods."""
    return _statement(ticker, freq, as_of_date, "Balance Sheet", "资产负债表", "stock_balance_sheet_by_report_em")


def get_cashflow_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    as_of_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Cash flow statement, latest periods."""
    return _statement(ticker, freq, as_of_date, "Cash Flow", "现金流量表", "stock_cash_flow_sheet_by_report_em")


def get_income_statement_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    as_of_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Income statement, latest periods."""
    return _statement(ticker, freq, as_of_date, "Income Statement", "利润表", "stock_profit_sheet_by_report_em")
