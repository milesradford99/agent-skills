"""Tests for the rescue-a-stock collector. Run with: python3 -m unittest discover -s tests"""

import datetime as dt
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "rescue-a-stock" / "references"))

import collect  # noqa: E402


def closes(values):
    return [(f"d{i:03d}", float(v)) for i, v in enumerate(values)]


class IndexMetricsTest(unittest.TestCase):
    def test_drawdown_uses_the_highest_close(self):
        m = collect.index_metrics(closes([100] * 30 + [200] + [150] * 25))
        self.assertEqual(m["peak_close"], 200)
        self.assertEqual(m["drawdown"], -25.0)

    def test_low_is_measured_after_the_peak(self):
        m = collect.index_metrics(closes([50] * 30 + [200, 120, 150, 160, 170, 180, 170]))
        self.assertEqual(m["low_close"], 120)
        self.assertEqual(m["sessions_since_low"], 5)

    def test_new_low_has_zero_sessions_since(self):
        m = collect.index_metrics(closes([100] * 30 + [90, 80, 70]))
        self.assertEqual(m["sessions_since_low"], 0)

    def test_window_drops_highs_older_than_250_sessions(self):
        m = collect.index_metrics(closes([999] + [100] * 260))
        self.assertEqual(m["peak_close"], 100)


class TriggerTest(unittest.TestCase):
    def test_speed_level_is_six_percent_below_the_close_that_drops_off(self):
        levels = collect.trigger_levels(closes([100, 100, 100, 100, 100]), 200)
        self.assertEqual(levels["next_close_for_5d_speed"], 94.0)
        self.assertEqual(levels["minus_20pct_from_peak"], 160.0)


class LeverageTest(unittest.TestCase):
    def test_margin_is_measured_from_its_peak(self):
        rows = [{"DIM_DATE": f"2026-10-{30 - i:02d} 00:00:00", "RZRQYE": b} for i, b in enumerate([2.4e12, 2.5e12, 2.6e12, 2.7e12, 2.8e12, 3.0e12])]
        m = collect.margin_metrics(rows)
        self.assertEqual(m["peak_tn"], 3.0)
        self.assertEqual(m["off_peak"], -20.0)

    def test_pledge_units(self):
        rows = [{"TRADE_DATE": "2026-10-30 00:00:00", "PLEDGE_MARKET_VALUE": 225561942.9, "PM_RATIO": 260.9, "PLEDGE_CO_NUM": 2214}]
        p = collect.pledge_metrics(rows)
        self.assertEqual(p["value_tn"], 2.256)
        self.assertEqual(p["ratio_pct_inferred"], 2.61)


class FuturesTest(unittest.TestCase):
    def test_third_friday(self):
        self.assertEqual(collect.third_friday(2026, 11), dt.date(2026, 11, 20))
        self.assertEqual(collect.third_friday(2027, 3), dt.date(2027, 3, 19))

    def test_contracts_skip_a_near_expiry(self):
        picked = [m for m, _ in collect.futures_contracts(dt.date(2026, 11, 15))]
        self.assertEqual(picked, ["2612", "2703"])

    def test_contracts_cross_the_year(self):
        picked = [m for m, _ in collect.futures_contracts(dt.date(2026, 12, 25))]
        self.assertEqual(picked, ["2701", "2703"])

    def test_serial_month_then_quarter(self):
        picked = [m for m, _ in collect.futures_contracts(dt.date(2026, 11, 2))]
        self.assertEqual(picked, ["2611", "2612"])

    def test_basis_sign_and_scale(self):
        basis = collect.annualised_basis(99, 100, dt.date(2026, 12, 31), dt.date(2026, 7, 4))
        self.assertAlmostEqual(basis, -2.0, places=1)

    def test_parse_sina_future(self):
        self.assertEqual(collect.parse_sina_future('var hq_str_nf_IM2612="6137.2,6343,6070,6273,287361";'), 6273.0)


class TurnoverTest(unittest.TestCase):
    def test_z_excludes_the_last_value(self):
        amounts = [10.0, 12.0] * 30 + [111.0]
        self.assertGreater(collect.turnover_z(amounts), 80)


class CollectTest(unittest.TestCase):
    def test_a_failed_feed_is_reported_not_filled(self):
        with unittest.mock.patch.object(collect, "get", side_effect=OSError("blocked")):
            snapshot = collect.collect(dt.date(2026, 11, 2))
        self.assertEqual(snapshot["indices"], {})
        self.assertIn("SSE: OSError: blocked", snapshot["missing"])
        self.assertIn("Missing:", collect.render(snapshot))


if __name__ == "__main__":
    unittest.main()
