"""Test forecast formulas, missing observations and protection against look-ahead bias."""
import math
import unittest
import pandas as pd
from forecasting import development_experiment, predict_ma4, predict_naive, ses_state_and_loss, validate_weekly_data


def weekly_sample():
    return pd.DataFrame({"week_start": pd.date_range("2020-01-06", periods=32, freq="W-MON"),
                         "order_count": [float(10 + i) for i in range(32)]})


class ForecastingTests(unittest.TestCase):
    def test_hand_calculated_predictions(self):
        history = [100, 120, 80, 140]
        self.assertEqual(predict_naive(history), 140)
        self.assertEqual(predict_ma4(history), 110)
        level, sse, count = ses_state_and_loss([100, 120, 80], 0.5)
        self.assertEqual((level, sse, count), (95, 1300, 2))

    def test_gap_is_not_compressed_or_imputed(self):
        self.assertEqual(predict_naive([100, math.nan, 120, 80]), 80)
        self.assertTrue(math.isnan(predict_ma4([100, math.nan, 120, 80])))
        self.assertTrue(math.isnan(predict_naive([100, math.nan])))
        self.assertEqual(ses_state_and_loss([100, math.nan, 120], 0.5)[0], 110)

    def test_known_mae_on_linear_series(self):
        predictions, metrics, _, protocol = development_experiment(weekly_sample(), 8, 4)
        self.assertEqual(len(predictions), 20)
        self.assertEqual(protocol["ses_alpha"], 1.0)
        scores = metrics.set_index("method")["mae"]
        self.assertEqual(scores["naive"], 1.0)
        self.assertEqual(scores["ma4"], 2.5)
        self.assertEqual(scores["ses"], 1.0)
        self.assertFalse(protocol["final_test_evaluated"])

    def test_all_methods_scored_on_identical_weeks(self):
        weekly = weekly_sample()
        weekly.loc[10, "order_count"] = math.nan
        predictions, metrics, _, protocol = development_experiment(weekly, 8, 4)
        self.assertEqual(protocol["common_evaluated_weeks"], 15)
        self.assertEqual(metrics["evaluated_weeks"].unique().tolist(), [15])
        self.assertEqual(int((~predictions["scored"]).sum()), 5)

    def test_reserved_final_values_do_not_change_development(self):
        original = weekly_sample()
        changed = original.copy()
        changed.loc[28:, "order_count"] = 99999
        first = development_experiment(original, 8, 4)
        second = development_experiment(changed, 8, 4)
        for i in range(3):
            pd.testing.assert_frame_equal(first[i], second[i])

    def test_target_and_future_values_do_not_change_earlier_predictions(self):
        original = weekly_sample()
        changed = original.copy()
        changed.loc[12:, "order_count"] = 99999
        first = development_experiment(original, 8, 4)[0]
        second = development_experiment(changed, 8, 4)[0]
        earlier = first["week_start"] <= original.loc[12, "week_start"]
        cols = ["week_start", "naive", "ma4", "ses"]
        pd.testing.assert_frame_equal(first.loc[earlier, cols], second.loc[earlier, cols])

    def test_missing_calendar_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "consecutive Mondays"):
            validate_weekly_data(weekly_sample().drop(index=4))

    def test_invalid_counts_are_rejected(self):
        for invalid in [-1, 2.5, math.inf, "invalid"]:
            weekly = weekly_sample().astype({"order_count": object})
            weekly.loc[0, "order_count"] = invalid
            with self.assertRaises(ValueError):
                validate_weekly_data(weekly)


if __name__ == "__main__":
    unittest.main()
