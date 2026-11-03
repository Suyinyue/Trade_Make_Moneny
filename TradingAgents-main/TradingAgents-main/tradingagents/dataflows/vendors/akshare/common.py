"""What the akshare (A-share) vendor calls share: symbol mapping and retries.

The pipeline speaks Yahoo's spelling of an A-share ticker (``600519.SS``,
``000001.SZ``, ``399001.SZ``), while akshare wants the exchange-prefixed code
(``sh600519``, ``sz000001``, ``sz399001``) and picks a different endpoint for an
index, a stock and an ETF. ``resolve`` maps one to the other, purely
syntactically, and refuses anything that is not an A-share instrument so the
router can fall through to the next configured vendor (yfinance covers the
rest of the world).

Sina's endpoints are the ones exercised here: the Eastmoney (``*_em``) ones are
often unreachable from mainland networks, which is also why the project keeps an
akshare-based pipeline of its own.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError

logger = logging.getLogger(__name__)

# A tradable A-share code is six digits; the exchange is either given as a Yahoo
# suffix (SS/SH = Shanghai, SZ = Shenzhen, BJ = Beijing) or inferred from the
# first digits. SSE stocks start 6/9, SZSE 0/2/3, BSE 4/8/920.
_CODE = re.compile(r"^(\d{6})(?:\.(SS|SH|SZ|BJ))?$")

_SHANGHAI_SUFFIXES = {"SS", "SH"}
_SHENZHEN_SUFFIX = "SZ"
_BEIJING_SUFFIX = "BJ"


@dataclass(frozen=True)
class AShareSymbol:
    """One A-share instrument: its Yahoo spelling, bare code, exchange and kind."""

    yahoo: str
    code: str
    exchange: str   # "sh" | "sz" | "bj"
    kind: str       # "stock" | "index" | "etf"

    @property
    def ak(self) -> str:
        """The exchange-prefixed code akshare expects, e.g. ``sh600519``."""
        return f"{self.exchange}{self.code}"

    @property
    def is_index(self) -> bool:
        return self.kind == "index"


def _kind(exchange: str, code: str) -> str:
    """Classify by exchange and code range, the way the exchanges allocate them."""
    if exchange == "sh":
        if code.startswith("000") or code.startswith("950"):
            return "index"          # SSE indices: 000001 上证, 000300 沪深300
        if code[:2] in {"50", "51", "52", "56", "58"}:
            return "etf"            # SSE-listed ETFs: 510300, 588000
        return "stock"
    if exchange == "sz":
        if code.startswith("399"):
            return "index"          # SZSE indices: 399001 深证成指, 399006 创业板指
        if code[:2] in {"15", "16", "18"}:
            return "etf"            # SZSE-listed ETFs: 159915, 161725
        return "stock"
    return "stock"                  # Beijing Stock Exchange: stocks only


def _exchange_from_code(code: str) -> str | None:
    """Infer the exchange of a bare six-digit code, or None when it is not one."""
    if code[:3] == "920" or code[0] in "48":
        return "bj"
    if code[0] in "569":
        return "sh"          # 6xx stocks, 5xx funds/ETFs, 9xx B-shares
    if code[0] in "023":
        return "sz"
    return None


def resolve(symbol: str) -> AShareSymbol:
    """Map a pipeline symbol to its akshare identity.

    Accepts ``600519.SS``, ``600519.SH``, ``000001.SZ``, ``399001.SZ``,
    ``830799.BJ`` and bare six-digit codes. Raises ``NoMarketDataError`` for
    anything else (a US or HK ticker, an index Yahoo spells ``^GSPC``), which
    the router treats as "this vendor has no rows" and falls through to the
    next configured vendor.
    """
    raw = (symbol or "").strip().upper()
    match = _CODE.match(raw)
    if not match:
        raise NoMarketDataError(
            symbol, symbol, "not an A-share/ETF/index code akshare serves"
        )

    code, suffix = match.group(1), match.group(2)
    if suffix in _SHANGHAI_SUFFIXES:
        exchange = "sh"
    elif suffix == _SHENZHEN_SUFFIX:
        exchange = "sz"
    elif suffix == _BEIJING_SUFFIX:
        exchange = "bj"
    else:
        exchange = _exchange_from_code(code)

    if exchange is None:
        raise NoMarketDataError(
            symbol, symbol, "cannot tell the exchange of this six-digit code"
        )

    # A Shanghai ``000xxx`` code is an index (SSE stocks never start with 000);
    # a Shenzhen ``000xxx`` is a stock (000001 平安银行), while 399xxx is the index.
    kind = _kind(exchange, code)
    yahoo = f"{code}.{'BJ' if exchange == 'bj' else 'SS' if exchange == 'sh' else 'SZ'}"
    return AShareSymbol(yahoo=yahoo, code=code, exchange=exchange, kind=kind)


# akshare passes no timeout to its HTTP calls, so a proxy or CDN that accepts the
# connection and then stalls would hang a run forever. Each call is bounded here.
REQUEST_TIMEOUT_SECONDS = 120


def _call_with_timeout(func, timeout: float):
    """``func()`` with a hard deadline, run on a daemon thread so a stall cannot
    keep the interpreter alive at exit."""
    box: dict = {}

    def run():
        try:
            box["value"] = func()
        except BaseException as exc:  # noqa: BLE001 — re-raised on the caller's thread
            box["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"no answer within {timeout:.0f}s")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def ak_retry(func, attempts: int = 2, base_delay: float = 1.5,
             timeout: float = REQUEST_TIMEOUT_SECONDS):
    """Run one akshare request, retrying a transport failure and reporting it as unavailable.

    akshare raises whatever ``requests`` raised, and those say nothing about the
    symbol: the router must try the next vendor rather than report "no data".
    An empty answer is not raised here — the caller inspects the frame.
    """
    for attempt in range(attempts + 1):
        try:
            return _call_with_timeout(func, timeout)
        except Exception as exc:  # noqa: BLE001 — every akshare failure is transport-level
            if attempt < attempts:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "akshare request failed (%s), retrying in %.0fs (attempt %d/%d)",
                    type(exc).__name__, delay, attempt + 1, attempts,
                )
                time.sleep(delay)
            else:
                raise VendorUnavailableError(
                    f"akshare request failed: {type(exc).__name__}: {exc}"
                ) from exc
    return None


def empty(symbol: str, resolved: AShareSymbol, what: str) -> NoMarketDataError:
    """The typed "this vendor has no rows" error for an empty akshare answer."""
    return NoMarketDataError(symbol, resolved.yahoo, f"no {what}")
