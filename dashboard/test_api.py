"""
Test suite for dashboard API and MT5 service.
"""

import os
import sys
import unittest
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.mt5_service import (
    get_total_profit,
    get_overview_metrics,
    get_symbol_wise_records,
    get_symbol_wise_performance,
    ensure_mt5_connected
)
from dashboard.server import parse_datetime_param, DashboardAPIHandler


class TestDashboardAPI(unittest.TestCase):
    def test_date_parser(self):
        dt1 = parse_datetime_param("2026-01-01", is_end=False)
        self.assertEqual(dt1, datetime(2026, 1, 1, 0, 0, 0))

        dt2 = parse_datetime_param("2026-11-23", is_end=True)
        self.assertEqual(dt2, datetime(2026, 11, 23, 23, 59, 59))

    def test_total_profit_function_signature(self):
        res = get_total_profit(datetime(2026, 1, 1), datetime(2026, 1, 31))
        self.assertIsInstance(res, float)

    def test_overview_metrics_signature(self):
        res = get_overview_metrics(datetime(2026, 1, 1), datetime(2026, 11, 23))
        self.assertIn("status", res)
        self.assertIn("net_profit", res)
        self.assertIn("win_rate", res)
        self.assertIn("profit_factor", res)
        self.assertIn("total_trades", res)

    def test_symbol_wise_records(self):
        records = get_symbol_wise_records(datetime(2026, 1, 1), datetime(2026, 11, 23), force_sample=True)
        self.assertIsInstance(records, list)
        self.assertTrue(len(records) > 0)
        first = records[0]
        self.assertIn("pair", first)
        self.assertIn("trades", first)
        self.assertIn("win_rate", first)
        self.assertIn("net_pnl", first)

    def test_static_files_exist(self):
        html_file = os.path.join(BASE_DIR, "index.html")
        css_file = os.path.join(BASE_DIR, "static", "css", "style.css")
        js_file = os.path.join(BASE_DIR, "static", "js", "app.js")
        self.assertTrue(os.path.exists(html_file))
        self.assertTrue(os.path.exists(css_file))
        self.assertTrue(os.path.exists(js_file))


if __name__ == "__main__":
    unittest.main()
