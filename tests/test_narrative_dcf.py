"""Tests for the narrative-dcf-valuation engine. Run with: python3 -m unittest discover -s tests"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "narrative-dcf-valuation" / "references"))

import narrative_dcf as nd  # noqa: E402

# Table 1-3 of the book: forward PE by discount rate (rows) and ceiling multiple m (columns), n = 10.
TABLE_1_3 = {
    0.05: [12.5, 20.0, 33.4, 45.7, 68.9, 122.1, 219.7, 311.2],
    0.06: [10.7, 16.7, 27.3, 37.0, 55.2, 97.0, 173.1, 244.3],
    0.07: [9.3, 14.3, 23.0, 30.9, 45.6, 79.3, 140.5, 197.6],
    0.08: [8.3, 12.5, 19.8, 26.3, 38.6, 66.3, 116.5, 163.3],
    0.10: [6.9, 10.0, 15.3, 20.1, 28.8, 48.6, 84.1, 116.9],
    0.12: [5.9, 8.3, 12.4, 16.0, 22.6, 37.3, 63.5, 87.7],
}
MS = [0.5, 1, 2, 3, 5, 10, 20, 30]

# Table 1-8: market-cap-to-terminal-profit multiple K for no-earnings companies, n = 3, 5, 10, 15.
TABLE_1_8 = {
    0.05: [19.1, 18.2, 16.2, 14.5],
    0.07: [13.4, 12.5, 10.7, 9.3],
    0.08: [11.6, 10.8, 9.1, 7.7],
    0.10: [9.1, 8.3, 6.8, 5.6],
    0.12: [7.5, 6.7, 5.3, 4.2],
    0.15: [5.8, 5.1, 3.8, 3.0],
}


class BookTablesTest(unittest.TestCase):
    def test_table_1_3(self):
        for r, row in TABLE_1_3.items():
            for m, want in zip(MS, row):
                self.assertAlmostEqual(nd.pe1(m, r), want, delta=0.051, msg=f"r={r} m={m}")

    def test_table_1_8(self):
        for r, row in TABLE_1_8.items():
            for n, want in zip((3, 5, 10, 15), row):
                self.assertAlmostEqual(nd.K_arith(r, n), want, delta=0.051, msg=f"r={r} n={n}")

    def test_worked_examples_1_1_and_1_2(self):
        self.assertAlmostEqual(nd.V_geo(2, 0.10, 10), 16.4, delta=0.05)
        self.assertAlmostEqual(nd.V_geo(2, 0.10, 5), 18.1, delta=0.05)
        self.assertAlmostEqual(nd.pe1(2, 0.10, 5), 15.8, delta=0.05)


class InverseTest(unittest.TestCase):
    def test_implied_m_round_trips(self):
        for m in (0.3, 1, 3, 10, 30):
            self.assertAlmostEqual(nd.implied_m_from_pe1(nd.pe1(m, 0.10), 0.10), m, places=4)

    def test_flat_earnings_pe10_implies_r10(self):
        self.assertAlmostEqual(nd.implied_r_from_pe1(10.0, 1.0), 0.10, places=6)

    def test_perpetual_growth_is_exact_not_book_shortcut(self):
        self.assertAlmostEqual(nd.pe1(10, 0.10, 10, 0.02), 56.2, delta=0.05)
        with self.assertRaises(ValueError):
            nd.V_geo(2, 0.05, 10, 0.05)


class AuctionTest(unittest.TestCase):
    def test_half_capacity_clears_at_mean(self):
        self.assertAlmostEqual(nd.auction_price(10, 3, 50, 100), 10, places=9)

    def test_more_attention_raises_price_convexly(self):
        y1, y2, y3 = (nd.auction_price(10, 3, 100, x) for x in (1000, 2000, 3000))
        self.assertGreater(y2, y1)
        self.assertGreater(y3, y2)

    def test_rejects_impossible_capacity(self):
        with self.assertRaises(ValueError):
            nd.auction_price(10, 3, 200, 100)


if __name__ == "__main__":
    unittest.main()
