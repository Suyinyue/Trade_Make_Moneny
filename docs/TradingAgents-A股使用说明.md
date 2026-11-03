# TradingAgents 分析 A 股：akshare 数据源接入说明

本目录下的 `TradingAgents-main/TradingAgents-main` 在原版基础上增加了一个 **akshare 数据供应商**，
让 A 股（沪深北）的行情、指标、公告/新闻、财报走国内数据源，而不是 Yahoo Finance。

## 一、环境

```
E:\Work\MakeMoney\venv-ta\        # 独立虚拟环境（Python 3.12.8）
```

> 不要用 `MakeMoney\venv`。那个环境是 akshare 取数管线用的，pandas 是 2.3.x；
> TradingAgents 要求 pandas >= 3.0.6，升级会破坏原有脚本。

安装方式（已改为 editable，改了源码立即生效）：

```powershell
E:\Work\MakeMoney\venv-ta\Scripts\python.exe -m pip install -e "E:\Work\MakeMoney\TradingAgents-main\TradingAgents-main"
E:\Work\MakeMoney\venv-ta\Scripts\python.exe -m pip install akshare
```

## 二、配置

`TradingAgents-main\TradingAgents-main\.env`（已在当前目录创建）：

```ini
DEEPSEEK_API_KEY=sk-...
TRADINGAGENTS_LLM_PROVIDER=deepseek
TRADINGAGENTS_QUICK_THINK_LLM=deepseek-flash
TRADINGAGENTS_DEEP_THINK_LLM=deepseek-v4-pro
TRADINGAGENTS_OUTPUT_LANGUAGE=Chinese
TRADINGAGENTS_RESULTS_DIR=E:\Work\MakeMoney\output\tradingagents
```

`.env` 从**当前工作目录**向上查找，所以要么在仓库目录里运行，要么把 `.env` 放到 `E:\Work\MakeMoney`。
这个文件里有密钥，不要提交到公开仓库或发给别人。

## 三、代码写法

A 股用 Yahoo 的交易所后缀，akshare 供应商会自动转换：

| 你输入 | 含义 | akshare 代码 |
|---|---|---|
| `600519.SS` | 上交所股票（贵州茅台） | `sh600519` |
| `000001.SZ` | 深交所股票（平安银行） | `sz000001` |
| `300750.SZ` | 创业板（宁德时代） | `sz300750` |
| `688981.SS` | 科创板（中芯国际） | `sh688981` |
| `830799.BJ` | 北交所 | `bj830799` |
| `000001.SS` | 上证指数（SS 后缀的 000 段是指数） | `sh000001` |
| `399001.SZ` | 深证成指 | `sz399001` |
| `510300.SS` | 上交所 ETF（沪深 300ETF） | `sh510300` |
| `159915.SZ` | 深交所 ETF（创业板 ETF） | `sz159915` |

不带后缀的 6 位代码也能识别（按号段推断交易所），但 **000 开头建议带后缀**：
`000001` 默认当作深市股票（平安银行），要上证指数请写 `000001.SS`。

## 四、数据源映射

| 数据 | 主源（akshare） | 不可用时的后备 |
|---|---|---|
| 日线 OHLCV | 新浪 `stock_zh_a_daily`（前复权 qfq） | yfinance |
| 指数日线 | 新浪 `stock_zh_index_daily` | yfinance |
| ETF 日线 | 新浪 `fund_etf_hist_sina` → 东财 `fund_etf_hist_em` | yfinance |
| 技术指标 | 本地 stockstats 计算（与 Yahoo 源同一套指标） | — |
| 公司概况 | 巨潮 `stock_profile_cninfo` | 东财/雪球 → 只给财务指标 |
| 财务报表 | 新浪 `stock_financial_report_sina`（按 `公告日期` 做时点过滤，只保留关键科目） | 东财 `*_by_report_em` |
| 个股新闻 | 东财 `stock_news_em`（只覆盖最近几天）→ 巨潮公告 `stock_zh_a_disclosure_report_cninfo`（可按历史窗口查） | yfinance |
| 全局财经新闻 | 东财 `stock_info_global_em` → 财联社 | yfinance |
| 宏观（美国） | FRED（需 `FRED_API_KEY`） | — |
| 预测市场 | Polymarket | — |

默认 vendor 链写在 `tradingagents/default_config.py` 的 `data_vendors`：

```python
"core_stock_apis": "akshare,yfinance",
"technical_indicators": "akshare,yfinance",
"fundamental_data": "akshare,sec_edgar,yfinance",
"news_data": "akshare,yfinance",
```

链式回落：akshare 遇到非 A 股代码（`AAPL`、`0700.HK`、`BTC-USD`）会抛 `NoMarketDataError`，
router 自动切到下一个数据源 —— 所以同一个环境既能跑 A 股也能跑美股/港股/加密。

## 五、点时间（point-in-time）处理

回测时不能读到"未来"的数据，供应商层做了三件事：

1. **行情**：只取分析日（含）之前的数据；最新一根 K 线比分析日早超过 12 个自然日视为陈旧，拒绝使用。
2. **财报**：新浪报表带 `公告日期`，按"公告日期 <= 分析日"过滤 —— 相当于"按披露时点读报表"，
   后补的公告读不到，后来重述的数字仍按当时披露值。
3. **公司概况/估值**：cninfo 概况是"今天"的快照，没有历史版本，所以**分析日早于今天时会被主动隐藏**，
   返回一段说明而不是编造。这是原框架的完整性规则，不是 bug。

## 六、运行

```powershell
cd E:\Work\MakeMoney\TradingAgents-main\TradingAgents-main
E:\Work\MakeMoney\venv-ta\Scripts\tradingagents.exe --ticker 600519.SS --date 2026-10-30 --analysts market,news --save --no-show
```

交互式（选股票、日期、分析师、深度、语言）：

```powershell
E:\Work\MakeMoney\venv-ta\Scripts\tradingagents.exe
```

回测（日期网格 + 按 alpha 打分）：

```powershell
E:\Work\MakeMoney\venv-ta\Scripts\tradingagents.exe backtest 600519.SS,000001.SZ --start 2026-06-01 --end 2026-10-01 --every 7
```

输出位置（两处）：

```
E:\Work\MakeMoney\output\tradingagents\600519.SS\2026-10-30\
    reports\*.md              # 运行过程中实时落盘的各章节
    message_tool.log          # 全部消息与工具调用（含每次取数结果）

E:\Work\MakeMoney\output\tradingagents\reports\600519.SS_20261101_203721\
    complete_report.md / .html   # 最终报告（问题回答"Save report?"=是时生成）
    1_analysts\ 2_research\ 3_trading\ 4_risk\ 5_portfolio\
```

实测耗时（DeepSeek，1 轮辩论 / 1 轮风控）：单个分析师约 60–150 秒，
从开始到组合经理拍板约 8–10 分钟；三个分析师并行，总时长主要由辩论与风控决定。

决策记忆：`C:\Users\<你>\.tradingagents\memory\trading_memory.md`
（会记录每次决策，并在持有期结束后自动结算收益、生成反思，供下次决策参考）

## 七、网络与代理

本机 Windows 系统代理指向 `127.0.0.1:7890`，代理软件关闭时 Python 的 `requests` 仍会走它，
导致取数报 `ProxyError`。两种处理：

```powershell
# A. 打开代理软件（推荐，Yahoo 等境外源也要用）
# B. 临时绕过代理，只用直连（新浪等国内源够用）
$env:NO_PROXY="*"; $env:no_proxy="*"
```

注意：绕过代理后，需要 Yahoo 的数据（美股行情、内部人交易）可能不可用，A 股分析不受影响。

## 八、已知限制

- **东财接口不稳定**：`stock_news_em` 在 akshare 1.17 上返回 KeyError，1.20.21 上正常；`stock_individual_info_em`
  仍会返回 JSONDecodeError。所以公司概况主用巨潮 `stock_profile_cninfo`，个股新闻失败时回落巨潮公告。
  宏观全局新闻用东财 `stock_info_global_em`（只覆盖最近 1–2 天，更早的窗口会明确回"数据不可用"而不是"没有新闻"）。
- **akshare 调用加了 120 秒硬超时**：它的底层请求不带 timeout，代理/CDN 卡住会把整个运行挂死；超时后按"该供应商不可用"处理。
- **行情只取近 5 年**（与原版 yfinance 一致），分析更早的日期会返回无数据。
- **前复权**：历史价格会随分红除权变化，横截面上指标没问题，但极严格的历史复盘可用原始价重新计算。
- **情绪分析（StockTwits/Reddit）对 A 股无意义**，建议 A 股只选 `market,news,fundamentals`。
- **成本**：一次运行是几十次 LLM 调用；`--analysts market,news` + `max_debate_rounds=1` 最省。
- 输出为研究参考，不构成投资建议。

## 九、代码位置

```
tradingagents/dataflows/vendors/akshare/
    common.py        # 代码映射（600519.SS -> sh600519）、重试
    ohlcv.py         # 日线抓取 + 缓存 + 防前视 + 陈旧校验
    market.py        # get_stock_data / get_indicators
    news.py          # 个股新闻/公告、全局财经新闻
    fundamentals.py  # 公司概况、财务指标、三张报表
```

改动过的原有文件（都很小）：

- `tradingagents/dataflows/router.py`：注册 `akshare` 供应商
- `tradingagents/default_config.py`：默认 vendor 链加入 akshare
- `tradingagents/dataflows/vendors/yahoo/snapshot.py`：验证快照按配置的行情源取数
- `tests/test_dataflows_config.py`、`tests/test_layering.py`：同步默认值与供应商库清单
