"""Chinese-language news from akshare, for the News Analyst.

Yahoo's feed carries almost nothing about A-share companies, so the per-ticker
feed comes from Eastmoney's news search and the macro feed from the financial
newswires akshare wraps. Both are trimmed to the analysis window so a backtest
never reads a later headline, and an empty answer over a window the feed never
covered is reported as unavailable rather than as "no news".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from dateutil.relativedelta import relativedelta

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.date_window import coverage_gap, in_window
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.vendors.akshare.common import ak_retry, resolve

_TITLE_COLUMNS = ("新闻标题", "公告标题", "标题", "title")
_CONTENT_COLUMNS = ("新闻内容", "摘要", "内容", "summary", "content")
_TIME_COLUMNS = ("发布时间", "公告时间", "时间", "发布日期", "pub_time", "date")
_DATE_COLUMNS = ("发布日期", "日期")
_SOURCE_COLUMNS = ("文章来源", "简称", "来源", "source", "publisher")
_LINK_COLUMNS = ("新闻链接", "公告链接", "链接", "url", "link")


def _first(frame: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in frame.columns), None)


_CST = timezone(timedelta(hours=8))


def _parse_time(value) -> datetime | None:
    """A vendor timestamp as an aware datetime (Chinese sources stamp Beijing time).

    ``in_window`` compares in UTC, so a naive Beijing timestamp read as UTC would
    shift every article eight hours later and let a late-evening one drift into
    the next day's window.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        parsed = pd.to_datetime(str(value), errors="coerce")
    except (ValueError, TypeError):
        return None
    if pd.isna(parsed):
        return None
    moment = parsed.to_pydatetime()
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=_CST)


def _articles(frame: pd.DataFrame) -> list[dict]:
    """Normalize an akshare news frame to title/content/time/source/link dicts."""
    if frame is None or frame.empty:
        return []

    title_col = _first(frame, _TITLE_COLUMNS)
    if title_col is None:
        return []
    content_col = _first(frame, _CONTENT_COLUMNS)
    time_col = _first(frame, _TIME_COLUMNS)
    date_col = _first(frame, _DATE_COLUMNS)
    source_col = _first(frame, _SOURCE_COLUMNS)
    link_col = _first(frame, _LINK_COLUMNS)

    out = []
    for _, row in frame.iterrows():
        title = str(row.get(title_col) or "").strip()
        if not title:
            continue
        when = _parse_time(row.get(time_col)) if time_col else None
        if when is None and date_col:
            when = _parse_time(row.get(date_col))
        content = str(row.get(content_col) or "").strip() if content_col else ""
        out.append({
            "title": title,
            "content": content.replace("\n", " ")[:500],
            "time": when,
            "source": str(row.get(source_col) or "").strip() if source_col else "",
            "link": str(row.get(link_col) or "").strip() if link_col else "",
        })
    return out


def _format(articles: list[dict]) -> str:
    lines = []
    for article in articles:
        source = f" (source: {article['source']})" if article["source"] else ""
        lines.append(f"### {article['title']}{source}")
        if article["content"]:
            lines.append(article["content"])
        if article["link"]:
            lines.append(f"Link: {article['link']}")
        lines.append("")
    return "\n".join(lines)


def _safe_fetch(call):
    """One endpoint's frame, or None when it is missing or broken.

    Eastmoney's news payload has changed shape in some releases; a parse error
    there is a reason to use the next source, not to fail the tool.
    """
    try:
        frame = ak_retry(call)
    except Exception:  # noqa: BLE001
        return None
    return frame if frame is not None and not frame.empty else None


def _eastmoney_news(sym):
    import akshare as ak

    fetch = getattr(ak, "stock_news_em", None)
    return None if fetch is None else _safe_fetch(lambda: fetch(symbol=sym.code))


def _cninfo_filings(sym, start_date: str, end_date: str):
    import akshare as ak

    fetch = getattr(ak, "stock_zh_a_disclosure_report_cninfo", None)
    if fetch is None:
        return None
    return _safe_fetch(lambda: fetch(
        symbol=sym.code,
        market="沪深京",
        category="",
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
    ))


def get_news_akshare(ticker: str, start_date: str, end_date: str) -> str:
    """News/filings about an A-share company published in the window.

    Eastmoney's news search is the journalism feed but only carries the latest
    page, so it answers for recent windows only. cninfo's disclosure list is
    date-ranged and answers for older ones — filings rather than journalism,
    but dated, per-stock and always about the company.
    """
    sym = resolve(ticker)
    if sym.kind != "stock":
        raise NoMarketDataError(ticker, sym.yahoo, f"no company news for a {sym.kind}")

    limit = get_config()["news_article_limit"]
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    seen_times, answered = [], False
    for label, feed in (
        ("Eastmoney news", lambda: _eastmoney_news(sym)),
        ("cninfo filings", lambda: _cninfo_filings(sym, start_date, end_date)),
    ):
        frame = feed()
        if frame is None:
            continue
        answered = True
        articles = _articles(frame)
        seen_times.extend(a["time"] for a in articles)
        in_range = [a for a in articles if in_window(a["time"], start_dt, end_dt)]
        if in_range:
            body = _format(in_range[:limit])
            return (
                f"## {ticker} News (akshare/{label}), from {start_date} to {end_date}:\n\n{body}"
            )

    if not answered:
        raise VendorUnavailableError(f"no akshare news source answered for {sym.yahoo}")

    # Nothing in the window: say whether any feed could have seen it at all.
    gap = coverage_gap(
        seen_times, start_date, end_date, "akshare", f"news about {ticker}",
    )
    return gap or f"No news found for {ticker} between {start_date} and {end_date}"


def _global_source():
    """The first available macro-news endpoint, as (frame, label)."""
    import akshare as ak

    for label, name in (
        ("Eastmoney", "stock_info_global_em"),
        ("CLS", "stock_info_global_cls"),
    ):
        fetch = getattr(ak, name, None)
        if fetch is None:
            continue
        try:
            frame = ak_retry(fetch)
        except VendorUnavailableError:
            continue
        if frame is not None and not frame.empty:
            return frame, label
    return None, None


def get_global_news_akshare(
    as_of_date: str,
    look_back_days: int | None = None,
    limit: int | None = None,
) -> str:
    """Chinese market-wide headlines over the trailing window."""
    config = get_config()
    look_back_days = config["global_news_lookback_days"] if look_back_days is None else look_back_days
    limit = config["global_news_article_limit"] if limit is None else limit

    end_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
    start_dt = end_dt - relativedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    frame, label = _global_source()
    if frame is None:
        raise VendorUnavailableError("no akshare global-news endpoint answered")

    articles = _articles(frame)
    picked, seen = [], set()
    for article in articles:
        if not in_window(article["time"], start_dt, end_dt):
            continue
        if article["title"] in seen:
            continue
        seen.add(article["title"])
        picked.append(article)
        if len(picked) >= limit:
            break

    if not picked:
        # The feed serves its latest page, so "nothing in the window" may mean
        # the window predates what it carries rather than that nothing happened.
        gap = coverage_gap(
            (a["time"] for a in articles), start_date, as_of_date,
            f"akshare/{label} global news", "market news",
        )
        return gap or f"No global news found between {start_date} and {as_of_date}"

    return (
        f"## Global Market News (akshare/{label}), from {start_date} to {as_of_date}:\n\n"
        + _format(picked)
    )
