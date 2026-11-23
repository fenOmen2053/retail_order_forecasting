"""Test invoice-counting rules on small examples."""

import unittest
import pandas as pd
from main import prepare_weekly_orders


def records(rows):
    table = pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Quantity", "Price"])
    table["Invoice"] = table["Invoice"].astype("string")
    table["InvoiceDate"] = pd.to_datetime(table["InvoiceDate"])
    return table


class WeeklyPreparationTests(unittest.TestCase):
    def test_repeated_invoice_is_counted_once_and_cancellations_excluded(self):
        raw = records([
            ("1001", "2009-01-05", 1, 10),
            ("1001", "2009-01-05", 2, 15),
            ("1001", "2009-01-06", 1, 10),
            ("1002", "2009-01-12", 1, 20),
            ("C1002", "2009-01-18", -1, 20),
            ("A1003", "2009-01-18", 1, 20),
        ])
        weekly, conflicts, report = prepare_weekly_orders(raw)
        self.assertEqual(weekly["order_count"].tolist(), [1, 1])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(report["unique_sales_invoices_all_dates"], 2)
        self.assertEqual(report["invoice_ids_crossing_week_boundaries"], 0)

    def test_no_records_is_missing_but_a_week_with_only_cancellations_is_zero(self):
        raw = records([
            ("1001", "2009-01-05", 1, 10),
            ("C1001", "2009-01-12", -1, 10),
            ("1002", "2009-01-26", 1, 20),
            ("C1002", "2009-02-01", -1, 20),
        ])
        weekly, _, _ = prepare_weekly_orders(raw)
        self.assertEqual(weekly.loc[1, "order_count"], 0)
        self.assertTrue(pd.isna(weekly.loc[2, "order_count"]))
        self.assertFalse(weekly["is_assumed_zero"].any())
        zero_weekly, _, _ = prepare_weekly_orders(raw, assume_empty_weeks_zero=True)
        self.assertEqual(zero_weekly["order_count"].tolist(), [1, 0, 0, 1])
        self.assertEqual(int(zero_weekly["is_assumed_zero"].sum()), 1)

    def test_incomplete_boundary_weeks_are_excluded(self):
        raw = records([
            ("1001", "2009-01-06", 1, 10),
            ("1002", "2009-01-12", 1, 10),
            ("1003", "2009-01-30", 1, 10),
        ])
        weekly, _, report = prepare_weekly_orders(raw)
        self.assertEqual(weekly["week_start"].dt.strftime("%Y-%m-%d").tolist(),
                         ["2009-01-12", "2009-01-19"])
        self.assertEqual(report["counted_orders_in_observed_full_weeks"], 1)

    def test_invoice_spanning_weeks_is_flagged(self):
        raw = records([
            ("1001", "2009-01-05", 1, 10),
            ("1001", "2009-01-12", 1, 10),
            ("C1001", "2009-01-18", -1, 10),
        ])
        weekly, conflicts, report = prepare_weekly_orders(raw)
        self.assertEqual(weekly["order_count"].tolist(), [1, 0])
        self.assertTrue(conflicts.iloc[0]["crosses_week_boundary"])
        self.assertEqual(report["invoice_ids_crossing_week_boundaries"], 1)


if __name__ == "__main__":
    unittest.main()
