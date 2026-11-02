# Sources

Checked 2026-11-02. These public feeds are unofficial and can change or block without notice. `collect.py` lists any that fail. Quote the date each figure refers to.

## Data feeds

| Data | Source | Notes |
|---|---|---|
| Index closes | [Sina kline](https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=320) | Cross-check against CSIndex; agreed within 5bp in testing |
| CSI 2000 | [CSIndex](https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=932000&startDate=20260101&endDate=20261231) | Publishes later than Sina, so its last date can lag |
| Margin | [Eastmoney RPTA_RZRQ_LSHJ](https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ&columns=ALL&source=WEB&sortColumns=dim_date&sortTypes=-1&pageNumber=1&pageSize=5) | One session behind prices |
| Stock pledges | [Eastmoney RPT_CSDC_STATISTICS](https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_CSDC_STATISTICS&columns=ALL&source=WEB&sortColumns=TRADE_DATE&sortTypes=-1&pageNumber=1&pageSize=5) | Weekly. Value in 10,000 yuan. `PM_RATIO` has no published unit; it fits basis points of shares (987 was about 10% in 2018), so label the percentage as inferred |
| Futures | `https://hq.sinajs.cn/list=nf_IM2612` | Needs a `Referer: https://finance.sina.com.cn` header. Field 3 is the last price. GBK encoded |
| ETF turnover | [Tencent kline](https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=sh510300,day,2026-10-01,2026-11-02,30,) | Field 8 is amount |
| ETF shares | [SSE dataset](https://query.sse.com.cn/commonQuery.do?sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L&isPagination=true&pageHelp.pageSize=5&pageHelp.pageNo=1&STAT_DATE=2026-10-30&SEC_CODE=510300) | Needs a `Referer: https://www.sse.com.cn/` header. `TOT_VOL` is in 10,000 units. Shanghai funds only |
| Fund filings | [Eastmoney F10](https://fundf10.eastmoney.com/jjgg_510300_3.html) | Institution-held shares bound any single holder from above |
| Primary policy text | [PBOC](https://www.pbc.gov.cn/), [CSRC](https://www.csrc.gov.cn/), [NBS](https://www.stats.gov.cn/), [Xinhua](https://www.news.cn/) | Prefer these over any reprint |

Eastmoney klines, Yahoo, Stooq and the SZSE API were unreliable from this environment in 2026.

## Searches

Add the current month. Run each in Chinese and English where it makes sense, and use a deeper search mode when results come back old.

- Latest actions: `国家队 ETF 净流入 {月份}`, `中央汇金 公告 {月份}`, `China national team ETF {month}`
- Meetings: `央行 证监会 座谈会 {日期}`, `政治局会议 {月份} 资本市场`, `证监会 党委 会议 稳市场 {月份}`
- Tools: `股票回购增持再贷款 使用 额度 {月份}`, `互换便利 操作 {月份}`
- Snowballs: `雪球 敲入 {月份} 中证1000`, `场外衍生品 存续规模 {月份}`
- Quant and DMA: `量化私募 回撤 {月份}`, `DMA 平仓 {月份}`
- Spillover: `银行理财 赎回 {月份}`, `债基 赎回 {月份}`
- Supply: `IPO 节奏 证监会 {月份}`, `减持 新规 {月份}`
- Macro: `国家统计局 CPI PPI {月份}`, `GDP 平减指数 {季度}`

Search engines often return 2024 articles for snowball and pledge queries. Check the date on every hit, and don't report an old figure as current.

## Data traps

- **Intraday against close.** 6,124, 5,178, 3,373, 2,850, 2,638, 2,440 and 2,635 are intraday. Use closes.
- **T+1 conventions differ.** This playbook counts from the T-1 close, and many articles count from T0.
- **Bad prints.** CSI 2000's low of 2,585 on 2026-07-21 looks like a vendor error.
- **Backfill.** CSI 1000 before October 2014 and CSI 2000 before 2023 are backfilled.
- **Implausible press figures.** A claim that hundreds of quant products fell over 90% in nine trading days was discarded. Check whether a figure is possible before using it.
- **Basis isn't dividend-adjusted** in `collect.py`. IH near dividend season reads too deep, so it's left out.
- **Attribution.** Goldman, BofA and Bloomberg Intelligence flow figures are estimates with different scopes. Don't add them up.
- **Aggregators.** Many sites repost one anonymous line, so ten hits can be one source. Trace it back before counting it.
