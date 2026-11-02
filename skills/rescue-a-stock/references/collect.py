#!/usr/bin/env python3
"""Pull a dated snapshot of China A-share stress data from public endpoints.

Standard library only. A source that fails is listed under `missing`, never
guessed or filled in, so the reading can cap its confidence.

Usage:
    python3 collect.py [--json snapshot.json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
TIMEOUT = 20

INDICES = {
    "SSE": "sh000001",
    "SSE 50": "sh000016",
    "CSI 300": "sh000300",
    "CSI 500": "sh000905",
    "CSI 1000": "sh000852",
    "ChiNext": "sz399006",
    "STAR 50": "sh000688",
}
FUTURES = {"IF": "CSI 300", "IC": "CSI 500", "IM": "CSI 1000"}
ETF_TURNOVER = ("sh510300", "sh510050", "sh510500", "sh512100", "sz159915")
ETF_SHARES = ("510300", "510050", "510500", "512100")
PLEDGE_2018 = {"date": "2018-10-19", "value_tn": 4.299, "ratio_pct": 9.87}
SPEED_TRIGGER = -0.06  # the fall before money in Feb 2024, Apr 2025 and Jul 2026, over five sessions


def get(url: str, referer: str | None = None) -> bytes:
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT) as resp:
        return resp.read()


def get_json(url: str, referer: str | None = None):
    return json.loads(get(url, referer))


def pct(new: float, old: float) -> float:
    return round((new / old - 1) * 100, 2)


def index_metrics(closes: list[tuple[str, float]]) -> dict:
    """Levels and drawdown from (date, close) rows, oldest first. Closes only: intraday prints mislead."""
    window = closes[-250:]
    peak_at = max(range(len(window)), key=lambda i: window[i][1])
    after_peak = window[peak_at:]
    low_at = min(range(len(after_peak)), key=lambda i: after_peak[i][1])
    date, close = closes[-1]
    return {
        "date": date,
        "close": close,
        "chg_1d": pct(close, closes[-2][1]),
        "chg_5d": pct(close, closes[-6][1]),
        "chg_20d": pct(close, closes[-21][1]),
        "peak_date": window[peak_at][0],
        "peak_close": window[peak_at][1],
        "drawdown": pct(close, window[peak_at][1]),
        "low_date": after_peak[low_at][0],
        "low_close": after_peak[low_at][1],
        "sessions_since_low": len(after_peak) - 1 - low_at,
    }


def trigger_levels(closes: list[tuple[str, float]], peak_close: float) -> dict:
    """SSE levels to watch. These are past patterns, not official lines."""
    return {
        "next_close_for_5d_speed": round(closes[-5][1] * (1 + SPEED_TRIGGER), 1),
        "minus_20pct_from_peak": round(peak_close * 0.8, 1),
    }


def margin_metrics(rows: list[dict]) -> dict:
    """Rows newest first, balances in yuan."""
    balances = [r["RZRQYE"] for r in rows]
    peak_at = max(range(len(balances)), key=balances.__getitem__)
    return {
        "date": rows[0]["DIM_DATE"][:10],
        "balance_tn": round(balances[0] / 1e12, 3),
        "peak_tn": round(balances[peak_at] / 1e12, 3),
        "peak_date": rows[peak_at]["DIM_DATE"][:10],
        "off_peak": pct(balances[0], balances[peak_at]),
        "chg_5d": pct(balances[0], balances[5]),
    }


def pledge_metrics(rows: list[dict]) -> dict:
    """Rows newest first. Value arrives in 10,000 yuan; PM_RATIO has no published unit and fits basis points."""
    latest = rows[0]
    return {
        "date": latest["TRADE_DATE"][:10],
        "value_tn": round(latest["PLEDGE_MARKET_VALUE"] / 1e8, 3),
        "ratio_pct_inferred": round(latest["PM_RATIO"] / 100, 2),
        "firms": latest["PLEDGE_CO_NUM"],
        "vs_oct_2018": PLEDGE_2018,
    }


def third_friday(year: int, month: int) -> dt.date:
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(4 - first.weekday()) % 7 + 14)


def futures_contracts(today: dt.date) -> list[tuple[str, dt.date]]:
    """The next serial month and the next quarter month, skipping any within 10 days of expiry."""
    picked: list[tuple[str, dt.date]] = []
    year, month = today.year, today.month
    while len(picked) < 2:
        expiry = third_friday(year, month)
        is_quarter = month in (3, 6, 9, 12)
        if (expiry - today).days >= 10 and (not picked or (is_quarter and expiry > picked[0][1])):
            picked.append((f"{year % 100:02d}{month:02d}", expiry))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return picked


def annualised_basis(future: float, spot: float, expiry: dt.date, today: dt.date) -> float:
    """Negative means a discount. Not dividend-adjusted, so compare like with like."""
    return round((future / spot - 1) * 365 / (expiry - today).days * 100, 1)


def parse_sina_future(text: str) -> float:
    return float(text.split('"')[1].split(",")[3])


def turnover_z(amounts: list[float], lookback: int = 60) -> float:
    """Last value against the trailing mean and SD, excluding itself."""
    base = amounts[-lookback - 1 : -1]
    return round((amounts[-1] - statistics.mean(base)) / statistics.stdev(base), 2)


def sina_closes(symbol: str) -> list[tuple[str, float]]:
    url = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        f"?symbol={symbol}&scale=240&ma=no&datalen=320"
    )
    return [(r["day"], float(r["close"])) for r in get_json(url)]


def csi2000_closes(today: dt.date) -> list[tuple[str, float]]:
    start = (today - dt.timedelta(days=500)).strftime("%Y%m%d")
    url = (
        "https://www.csindex.com.cn/csindex-home/perf/index-perf"
        f"?indexCode=932000&startDate={start}&endDate={today:%Y%m%d}"
    )
    rows = get_json(url)["data"]
    return [(f"{r['tradeDate'][:4]}-{r['tradeDate'][4:6]}-{r['tradeDate'][6:]}", float(r["close"])) for r in rows]


def eastmoney(report: str, sort: str, size: int) -> list[dict]:
    query = urllib.parse.urlencode(
        {
            "reportName": report,
            "columns": "ALL",
            "source": "WEB",
            "sortColumns": sort,
            "sortTypes": -1,
            "pageNumber": 1,
            "pageSize": size,
        }
    )
    return get_json(f"https://datacenter-web.eastmoney.com/api/data/v1/get?{query}")["result"]["data"]


def etf_turnover(symbol: str, today: dt.date) -> dict:
    start = (today - dt.timedelta(days=140)).isoformat()
    url = (
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
        f"?param={symbol},day,{start},{today.isoformat()},100,"
    )
    rows = get_json(url)["data"][symbol]["day"]
    amounts = [float(r[8]) for r in rows]
    recent = [turnover_z(amounts[: i + 1]) for i in range(len(amounts) - 10, len(amounts))]
    return {"date": rows[-1][0], "z": recent[-1], "max_z_10d": max(recent)}


def sse_etf_shares(date: str) -> dict[str, float]:
    url = (
        "https://query.sse.com.cn/commonQuery.do?sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L"
        f"&isPagination=true&pageHelp.pageSize=2000&pageHelp.pageNo=1&STAT_DATE={date}&SEC_CODE="
    )
    rows = get_json(url, "https://www.sse.com.cn/")["pageHelp"]["data"]
    return {r["SEC_CODE"]: float(r["TOT_VOL"]) for r in rows if r["SEC_CODE"] in ETF_SHARES}


def etf_share_changes(calendar: list[str]) -> dict:
    """Share change over 5 and 20 sessions. Creation shows demand, never the buyer."""
    latest = {}
    latest_date = ""
    for date in reversed(calendar[-3:]):  # the exchange publishes after the close
        latest = sse_etf_shares(date)
        if latest:
            latest_date = date
            break
    if not latest:
        raise ValueError("no SSE share data for the last 3 sessions")
    at = calendar.index(latest_date)
    five, twenty = sse_etf_shares(calendar[at - 5]), sse_etf_shares(calendar[at - 20])
    return {
        "date": latest_date,
        "funds": {
            code: {"chg_5d": pct(latest[code], five[code]), "chg_20d": pct(latest[code], twenty[code])}
            for code in latest
            if code in five and code in twenty
        },
    }


def collect(today: dt.date) -> dict:
    snapshot: dict = {"as_of": today.isoformat(), "indices": {}, "missing": []}

    def attempt(name, fn):
        try:
            return fn()
        except Exception as err:  # every feed is unofficial: report the failure and carry on
            snapshot["missing"].append(f"{name}: {type(err).__name__}: {err}")
            return None

    series = {}
    for label, symbol in INDICES.items():
        closes = attempt(label, lambda s=symbol: sina_closes(s))
        if closes:
            series[label] = closes
            snapshot["indices"][label] = index_metrics(closes)
    closes = attempt("CSI 2000", lambda: csi2000_closes(today))
    if closes:
        snapshot["indices"]["CSI 2000"] = index_metrics(closes)

    if "SSE" in series:
        snapshot["sse_levels"] = trigger_levels(series["SSE"], snapshot["indices"]["SSE"]["peak_close"])

    rows = attempt("margin", lambda: eastmoney("RPTA_RZRQ_LSHJ", "dim_date", 260))
    if rows:
        snapshot["margin"] = margin_metrics(rows)
    rows = attempt("pledges", lambda: eastmoney("RPT_CSDC_STATISTICS", "TRADE_DATE", 3))
    if rows:
        snapshot["pledges"] = pledge_metrics(rows)

    snapshot["basis"] = {}
    for code, index in FUTURES.items():
        if index not in snapshot["indices"]:
            continue
        spot = snapshot["indices"][index]["close"]
        for month, expiry in futures_contracts(today):
            contract = f"{code}{month}"
            url = f"https://hq.sinajs.cn/list=nf_{contract}"
            text = attempt(contract, lambda: get(url, "https://finance.sina.com.cn").decode("gbk"))
            if text:
                last = attempt(contract, lambda t=text: parse_sina_future(t))
                if last:
                    snapshot["basis"][contract] = annualised_basis(last, spot, expiry, today)

    snapshot["etf_turnover"] = {}
    for symbol in ETF_TURNOVER:
        result = attempt(symbol, lambda s=symbol: etf_turnover(s, today))
        if result:
            snapshot["etf_turnover"][symbol[2:]] = result
    if "SSE" in series:
        result = attempt("ETF shares", lambda: etf_share_changes([d for d, _ in series["SSE"]]))
        if result:
            snapshot["etf_shares"] = result

    dates = [m["date"] for m in snapshot["indices"].values()]
    if dates:
        snapshot["latest_session"] = max(dates)
        snapshot["stale_days"] = (today - dt.date.fromisoformat(max(dates))).days
    return snapshot


def render(s: dict) -> str:
    out = [f"# A-share stress snapshot, pulled {s['as_of']}", ""]
    if s.get("latest_session"):
        out += [f"Latest session: {s['latest_session']} ({s['stale_days']} calendar days old)", ""]
    out += [
        "| Index | Date | Close | 1d % | 5d % | 20d % | From 250d high % | High date | Low date | Sessions since low |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for label, m in s["indices"].items():
        out.append(
            f"| {label} | {m['date']} | {m['close']:.2f} | {m['chg_1d']} | {m['chg_5d']} | {m['chg_20d']} "
            f"| {m['drawdown']} | {m['peak_date']} | {m['low_date']} | {m['sessions_since_low']} |"
        )
    if "sse_levels" in s:
        lv = s["sse_levels"]
        out += ["", f"SSE watch levels (past patterns, not official): next close for -6% in 5 sessions {lv['next_close_for_5d_speed']}; -20% from high {lv['minus_20pct_from_peak']}"]
    if "margin" in s:
        m = s["margin"]
        out += ["", f"Margin ({m['date']}): {m['balance_tn']}tn, {m['off_peak']}% from {m['peak_tn']}tn on {m['peak_date']}, 5d {m['chg_5d']}%"]
    if "pledges" in s:
        p = s["pledges"]
        base = p["vs_oct_2018"]
        out += ["", f"Pledges ({p['date']}): {p['value_tn']}tn, about {p['ratio_pct_inferred']}% of shares (inferred unit), {p['firms']} firms. {base['date']}: {base['value_tn']}tn, {base['ratio_pct']}%"]
    if s.get("basis"):
        out += ["", "Annualised basis, not dividend-adjusted: " + ", ".join(f"{k} {v}%" for k, v in s["basis"].items())]
    if s.get("etf_turnover"):
        out += ["", "ETF turnover z (60d): " + ", ".join(f"{k} {v['z']} (10d max {v['max_z_10d']})" for k, v in s["etf_turnover"].items())]
    if "etf_shares" in s:
        e = s["etf_shares"]
        out += ["", f"ETF share change to {e['date']}: " + ", ".join(f"{k} 5d {v['chg_5d']}% 20d {v['chg_20d']}%" for k, v in e["funds"].items())]
    out += ["", "Missing: " + ("; ".join(s["missing"]) if s["missing"] else "none")]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="also write the snapshot to this file")
    args = parser.parse_args(argv)
    snapshot = collect(dt.date.today())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, ensure_ascii=False, indent=2)
    print(render(snapshot))
    return 0 if snapshot["indices"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
