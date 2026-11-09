#!/usr/bin/env python3
"""《穿透叙事》空间叙事估值引擎 —— 邹佩轩 DCF 解析解的严格实现。
模型A（有业绩，等比匀速）: E_t = E0*m^(t/n), t=1..n；之后恒为 m*E0（可选稳态增长 g）。
  V = P/E0 = q(1-q^n)/(1-q) + m/((r-g)(1+r)^n),  q = m^(1/n)/(1+r)
  动态PE1 = V / m^(1/n)
模型B（当前无业绩，等差）: E_t = M*t/n, t=1..n；之后恒为 M。
  K = P/M = (1/n)*Σ t/(1+r)^t + 1/(r(1+r)^n)
拍卖机制: y = μ + σ·Φ⁻¹(1 - s/x)
"""
import argparse, json, math
from statistics import NormalDist

def V_geo(m, r, n=10, g=0.0):
    if r <= g: raise ValueError("要求 r > g")
    a = m ** (1.0 / n)
    pv = sum(a**t / (1 + r)**t for t in range(1, n + 1))
    return pv + m / ((r - g) * (1 + r)**n)

def pe1(m, r, n=10, g=0.0):
    return V_geo(m, r, n, g) / m ** (1.0 / n)

def K_arith(r, n):
    return sum((t / n) / (1 + r)**t for t in range(1, n + 1)) + 1 / (r * (1 + r)**n)

def solve(f, target, lo, hi, it=200):
    flo = f(lo) - target
    for _ in range(it):
        mid = math.sqrt(lo * hi)
        fm = f(mid) - target
        if (fm > 0) == (flo > 0): lo, flo = mid, fm
        else: hi = mid
    return math.sqrt(lo * hi)

def implied_m_from_pe1(pe, r, n=10, g=0.0):
    return solve(lambda m: pe1(m, r, n, g), pe, 1e-4, 1e4)

def implied_r_from_pe1(pe, m, n=10):
    return solve(lambda r: -pe1(m, r, n), -pe, 0.005, 1.0)

def auction_price(mu, sigma, s, x):
    if not 0 < s < x: raise ValueError("要求 0 < 流通市值容量 s < 关注资金 x")
    return mu + sigma * NormalDist().inv_cdf(1 - s / x)

def tables():
    ms = [0.5, 1, 2, 3, 5, 10, 20, 30]; rs = [.05, .06, .07, .08, .10, .12]
    print("表1-3 动态PE1 (n=10)  m→", ms)
    for r in rs: print(f"r={r:.0%}", [round(pe1(m, r), 1) for m in ms])
    print("表1-8 市值速算倍数 K (等差)  n→ [3,5,10,15]")
    for r in [.05, .07, .08, .10, .12, .15]: print(f"r={r:.0%}", [round(K_arith(r, n), 1) for n in (3, 5, 10, 15)])

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["tables", "implied", "fair", "nonprofit", "auction", "sens"])
    p.add_argument("--pe1", type=float, help="动态PE = 市值/下一财年净利润(一致预期)")
    p.add_argument("--mcap", type=float); p.add_argument("--e0", type=float, help="当年净利润")
    p.add_argument("--e1", type=float, help="下一年净利润")
    p.add_argument("--m", type=float, help="业绩天花板/当年业绩")
    p.add_argument("--M", type=float, help="无业绩公司的终局利润")
    p.add_argument("--r", type=float, default=0.10); p.add_argument("--n", type=int, default=10)
    p.add_argument("--g", type=float, default=0.0)
    p.add_argument("--mu", type=float); p.add_argument("--sigma", type=float)
    p.add_argument("--s", type=float); p.add_argument("--x", type=float)
    a = p.parse_args(); out = {}
    if a.mode == "tables": return tables()
    if a.mode == "implied":
        pe = a.pe1 or (a.mcap / a.e1)
        out = {"PE1": pe, "r": a.r, "implied_m(n=10)": implied_m_from_pe1(pe, a.r, 10, a.g),
               "implied_m_by_n": {n: round(implied_m_from_pe1(pe, a.r, n, a.g), 3) for n in (5, 8, 10, 12, 15)},
               "implied_r_if_m=1": implied_r_from_pe1(pe, 1.0)}
        if a.e0: out["ceiling_profit"] = out["implied_m(n=10)"] * a.e0
    elif a.mode == "fair":
        out = {"m": a.m, "r": a.r, "n": a.n, "g": a.g, "fair_PE1": pe1(a.m, a.r, a.n, a.g),
               "V=P/E0": V_geo(a.m, a.r, a.n, a.g)}
        if a.e1: out["fair_mcap"] = out["fair_PE1"] * a.e1          # 首选：书中口径，对 n 不敏感
        elif a.e0: out["fair_mcap"] = out["V=P/E0"] * a.e0           # 无 E1 时退而求其次，对 n 较敏感
        if "fair_mcap" in out and a.mcap: out["upside"] = out["fair_mcap"] / a.mcap - 1
    elif a.mode == "nonprofit":
        K = K_arith(a.r, a.n); out = {"K": K, "r": a.r, "n": a.n}
        if a.mcap: out["implied_terminal_profit"] = a.mcap / K
        if a.M: out["fair_mcap"] = a.M * K
    elif a.mode == "auction":
        out = {"auction_price": auction_price(a.mu, a.sigma, a.s, a.x), "drift": auction_price(a.mu, a.sigma, a.s, a.x) - a.mu}
    elif a.mode == "sens":
        ms = [0.3, 0.5, 0.7, 1, 1.5, 2, 3, 5, 10, 20]; rs = [.08, .09, .10, .11, .12]
        out = {f"r={r:.0%}": {m: round(pe1(m, r, a.n, a.g), 1) for m in ms} for r in rs}
    rd = lambda o: {k: rd(v) for k, v in o.items()} if isinstance(o, dict) else (round(o, 4) if isinstance(o, float) else o)
    print(json.dumps(rd(out), ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
