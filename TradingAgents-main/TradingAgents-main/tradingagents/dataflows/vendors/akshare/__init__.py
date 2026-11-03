"""A-share market, news and fundamentals data from akshare (Sina/Eastmoney).

Registered in the router as the ``akshare`` vendor. Its functions raise
``NoMarketDataError`` for any symbol they cannot serve (a US, HK or crypto
ticker), so a chain such as ``akshare,yfinance`` serves A-shares here and
everything else from the next vendor.
"""

from tradingagents.dataflows.vendors.akshare.fundamentals import (
    get_balance_sheet_akshare,
    get_cashflow_akshare,
    get_company_profile_akshare,
    get_fundamentals_akshare,
    get_income_statement_akshare,
)
from tradingagents.dataflows.vendors.akshare.market import (
    get_stock_data_akshare,
    get_stock_stats_indicators_window_akshare,
)
from tradingagents.dataflows.vendors.akshare.news import (
    get_global_news_akshare,
    get_news_akshare,
)

__all__ = [
    "get_balance_sheet_akshare",
    "get_cashflow_akshare",
    "get_company_profile_akshare",
    "get_fundamentals_akshare",
    "get_global_news_akshare",
    "get_income_statement_akshare",
    "get_news_akshare",
    "get_stock_data_akshare",
    "get_stock_stats_indicators_window_akshare",
]
