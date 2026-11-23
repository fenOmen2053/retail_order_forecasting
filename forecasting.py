"""Compare three one-week-ahead forecasting methods for the midterm experiment.

Each forecast uses observations available before its target week. By default,
the last 26 weeks are reserved for the final evaluation.
"""

import json
import math
from pathlib import Path

import pandas as pd


METHODS = ["naive", "ma4", "ses"]
LABELS = {"naive": "Naive", "ma4": "4-week moving average", "ses": "Simple exponential smoothing"}


def validate_weekly_data(weekly):
    """Validate the calendar and counts while retaining weeks with missing observations."""
    if not {"week_start", "order_count"}.issubset(weekly.columns):
        raise ValueError("Weekly data must contain week_start and order_count.")
    result = weekly.copy()
    result["week_start"] = pd.to_datetime(result["week_start"], errors="raise")
    dates = result["week_start"]
    if dates.isna().any() or dates.duplicated().any():
        raise ValueError("Week dates must be present and unique.")
    if (dates.dt.weekday != 0).any() or (dates != dates.dt.normalize()).any():
        raise ValueError("Each week_start must be a Monday at midnight.")
    if not dates.diff().iloc[1:].eq(pd.Timedelta(days=7)).all():
        raise ValueError("Weekly dates must be consecutive Mondays in ascending order.")
    values = pd.to_numeric(result["order_count"], errors="coerce")
    if (result["order_count"].notna() & values.isna()).any():
        raise ValueError("order_count contains a nonnumeric value.")
    for value in values.dropna():
        if not math.isfinite(float(value)) or value < 0 or value != int(value):
            raise ValueError("Observed order counts must be finite nonnegative integers.")
    result["order_count"] = values.astype(float)
    return result


def predict_naive(history):
    """Use the previous calendar week's count as the next forecast."""
    return float(history[-1]) if len(history) and pd.notna(history[-1]) else math.nan


def predict_ma4(history):
    """Forecast the mean count over the four preceding calendar weeks."""
    last_four = history[-4:]
    if len(last_four) != 4 or any(pd.isna(value) for value in last_four):
        return math.nan
    return sum(last_four) / 4


def ses_state_and_loss(history, alpha):
    """Update the SES level as alpha * observation + (1 - alpha) * previous level.

    The first observed count sets the initial level. Score each forecast before
    updating the level. When an observation is missing, keep the current level
    and skip the error calculation for that week.
    """
    if not 0 < alpha <= 1:
        raise ValueError("SES alpha must be greater than 0 and at most 1.")
    level = None
    squared_error = 0.0
    error_count = 0
    for value in history:
        if pd.isna(value):
            continue
        value = float(value)
        if level is None:
            level = value
            continue
        squared_error += (value - level) ** 2
        error_count += 1
        level = alpha * value + (1 - alpha) * level
    return level, squared_error, error_count


def select_alpha(training_values):
    """Select alpha using forecast errors from the initial training period only."""
    rows = []
    for step in range(1, 21):
        alpha = step / 20  # 0.05, 0.10, ..., 1.00.
        _, sse, count = ses_state_and_loss(training_values, alpha)
        if count < 4:
            raise ValueError("At least five observed training weeks are required for SES.")
        rows.append({"alpha": alpha, "training_sse": sse, "training_error_count": count})
    search = pd.DataFrame(rows)
    best = search.sort_values(["training_sse", "alpha"]).iloc[0]
    return float(best["alpha"]), search


def development_experiment(weekly, train_weeks=52, holdout_weeks=26):
    """Evaluate forecasts sequentially between training and the final holdout."""
    weekly = validate_weekly_data(weekly)
    if train_weeks < 8 or holdout_weeks < 1:
        raise ValueError("Use at least 8 training weeks and at least 1 reserved final week.")
    development_end = len(weekly) - holdout_weeks
    if development_end - train_weeks < 4:
        raise ValueError("At least four development weeks are required between train and holdout.")

    values = weekly["order_count"].tolist()
    alpha, search = select_alpha(values[:train_weeks])
    rows = []
    for index in range(train_weeks, development_end):
        # Stop before the target week to keep future observations out of the forecast.
        history = values[:index]
        level, _, _ = ses_state_and_loss(history, alpha)
        row = {
            "week_start": weekly.iloc[index]["week_start"],
            "actual": values[index],
            "naive": predict_naive(history),
            "ma4": predict_ma4(history),
            "ses": float(level),
        }
        rows.append(row)
    forecasts = pd.DataFrame(rows)

    # Score all three methods on the same target weeks.
    forecasts["scored"] = forecasts[["actual"] + METHODS].notna().all(axis=1)
    forecasts["exclusion_reason"] = ""
    forecasts.loc[forecasts["actual"].isna(), "exclusion_reason"] = "Missing target observation"
    missing_history = forecasts["actual"].notna() & ~forecasts["scored"]
    forecasts.loc[missing_history, "exclusion_reason"] = "Missing calendar history for at least one method"
    common = forecasts.loc[forecasts["scored"]]
    if len(common) < 4:
        raise ValueError("Fewer than four weeks can be scored by all three methods.")

    metrics = []
    naive_mae = float((common["actual"] - common["naive"]).abs().mean())
    for method in METHODS:
        forecasts[f"{method}_absolute_error"] = (forecasts["actual"] - forecasts[method]).abs()
        mae = float((common["actual"] - common[method]).abs().mean())
        improvement = 100 * (naive_mae - mae) / naive_mae if naive_mae > 0 else None
        metrics.append({
            "method": method,
            "method_name": LABELS[method],
            "mae": mae,
            "improvement_vs_naive_percent": improvement,
            "evaluated_weeks": len(common),
            "available_target_weeks": int(forecasts[["actual", method]].notna().all(axis=1).sum()),
        })
    comparison = pd.DataFrame(metrics).sort_values("mae", kind="stable").reset_index(drop=True)
    dates = weekly["week_start"]
    def period(start, stop):
        return {
            "first_week_start": str(dates.iloc[start].date()),
            "last_week_end": str((dates.iloc[stop - 1] + pd.Timedelta(days=6)).date()),
            "calendar_weeks": stop - start,
        }
    protocol = {
        "stage": "Preliminary development evaluation for midterm",
        "target": "Weekly distinct eligible sales invoice count",
        "horizon_weeks": 1,
        "training": period(0, train_weeks),
        "development": period(train_weeks, development_end),
        "reserved_final_test": period(development_end, len(weekly)),
        "final_test_evaluated": False,
        "ses_alpha": alpha,
        "ses_alpha_selection": "Grid 0.05 to 1.00 in steps of 0.05; minimum training one-step SSE; first observed value initializes level; alpha is then fixed.",
        "state_update": "After each development week, its observed value becomes available for the next one-week forecast.",
        "missing_week_policy": "No imputation. Naive requires the previous calendar week; MA4 requires four consecutive previous observations; SES retains its level at missing observations.",
        "metric": "MAE on the intersection of observed targets and predictions available from all methods; predictions are not rounded.",
        "common_evaluated_weeks": len(common),
        "excluded_development_weeks": int((~forecasts["scored"]).sum()),
        "missing_development_targets": int(forecasts["actual"].isna().sum()),
        "sources": [
            "https://otexts.com/fpp3/toolbox.html#time-series-cross-validation",
            "https://otexts.com/fpp3/exponential-smoothing.html#simple-exponential-smoothing",
        ],
    }
    return forecasts, comparison, search, protocol


def save_experiment_charts(forecasts, comparison, protocol, output_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    colors = {"naive": "#245A81", "ma4": "#BD5B26", "ses": "#398267"}
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(forecasts["week_start"], forecasts["actual"], color="#222222", linewidth=2.2, label="Actual")
    for method in METHODS:
        ax.plot(forecasts["week_start"], forecasts[method], color=colors[method], linewidth=1.4, label=LABELS[method])
    for date in forecasts.loc[~forecasts["scored"], "week_start"]:
        ax.axvspan(date, date + pd.Timedelta(days=7), color="#AAAAAA", alpha=0.13)
    ax.set(title="One-week-ahead forecasts on the development period",
           xlabel="Target week beginning Monday", ylabel="Number of sales invoices")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.07, 0.02, "Shaded weeks are excluded from the common MAE comparison. Final test weeks are not evaluated.", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(output_dir / "development_forecasts.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.barh(comparison["method_name"], comparison["mae"], color=[colors[m] for m in comparison["method"]])
    ax.invert_yaxis()
    ax.bar_label(bars, fmt="%.2f", padding=5)
    ax.set_xlim(0, max(comparison["mae"]) * 1.25 if max(comparison["mae"]) else 1)
    ax.set(title="Development MAE on identical target weeks", xlabel="Mean absolute error (orders)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.1, 0.02, f"{protocol['common_evaluated_weeks']} common weeks. Lower MAE is better. Preliminary results.", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(output_dir / "mae_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 3))
    stages = [("training", "Training", "#245A81"), ("development", "Development", "#BD5B26"),
              ("reserved_final_test", "Reserved final test", "#A1A7AD")]
    for key, label, color in stages:
        p = protocol[key]
        start = pd.Timestamp(p["first_week_start"])
        stop = pd.Timestamp(p["last_week_end"]) + pd.Timedelta(days=1)
        ax.barh(0, (stop - start).days, left=mdates.date2num(start), height=0.5, color=color)
        ax.text(mdates.date2num(start + (stop - start) / 2), 0,
                f"{label}\n{p['calendar_weeks']} weeks", ha="center", va="center", color="white", fontsize=10)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_yticks([])
    ax.set(title="Chronological experiment split", xlabel="Calendar date")
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_dir / "evaluation_split.png", dpi=180)
    plt.close(fig)


def write_experiment_notes(comparison, protocol, output_dir):
    lines = ["# Midterm forecasting experiment", "", "These are preliminary development results. The reserved final test has not been evaluated.", "", "## Methods", "",
             "- Naive: forecast the last calendar week's observed count.",
             "- MA4: forecast the mean of the four previous calendar weeks, excluding the target week.",
             "- SES: initialize the level with the first observed training count; update it as alpha * observation + (1 - alpha) * previous level. The forecast is the latest level available before the target week.", "", "## Protocol", ""]
    for key, title in [("training", "Initial training"), ("development", "Development"), ("reserved_final_test", "Reserved final test")]:
        p = protocol[key]
        lines.append(f"- {title}: {p['first_week_start']} to {p['last_week_end']} ({p['calendar_weeks']} calendar weeks).")
    lines.extend([
        f"- SES alpha: {protocol['ses_alpha']:.2f}, selected using initial training SSE only and then held fixed.",
        "- Training SSE is a parameter-fitting criterion, not the reported forecast accuracy.",
        "- Development evaluation advances one week at a time. Earlier development observations may update forecasts for later weeks; future observations are never used.",
        "- Missing weeks remain in the calendar. No zero or interpolated counts are invented. Naive and MA4 return unavailable forecasts when their required calendar history is missing. SES skips the update at a missing observation.",
        "- MAE is the mean of abs(actual - prediction). All methods are compared on the same intersection of eligible weeks, with unrounded predictions.",
        f"- Common evaluated weeks: {protocol['common_evaluated_weeks']}; excluded development weeks: {protocol['excluded_development_weeks']}.", "", "## Preliminary comparison", "",
        "| Method | MAE (orders) | Common evaluated weeks |", "|---|---:|---:|",
    ])
    for _, row in comparison.iterrows():
        lines.append(f"| {row['method_name']} | {row['mae']:.2f} | {int(row['evaluated_weeks'])} |")
    best = comparison.loc[comparison["mae"] == comparison["mae"].min(), "method_name"].tolist()
    lines.extend(["", "Lowest development MAE: " + ", ".join(best) + ".",
                  "This comparison is specific to the stated development dates and missing-data policy. It does not establish a universally best method. Inspect excluded weeks in development_forecasts.csv. The final test should be evaluated only after methods and preprocessing decisions are fixed.",
                  "", "## Sources", "",
                  "- [Forecast evaluation and time series cross-validation](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation)",
                  "- [Simple exponential smoothing](https://otexts.com/fpp3/exponential-smoothing.html#simple-exponential-smoothing)", ""])
    (output_dir / "experiment_notes.md").write_text("\n".join(lines), encoding="utf-8")


def run_midterm_experiment(weekly, output_dir, train_weeks=52, holdout_weeks=26):
    """Save the preliminary experiment tables, evaluation protocol and charts."""
    forecasts, comparison, search, protocol = development_experiment(weekly, train_weeks, holdout_weeks)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(output_dir / "development_forecasts.csv", index=False, date_format="%Y-%m-%d")
    comparison.to_csv(output_dir / "method_comparison.csv", index=False)
    search.to_csv(output_dir / "alpha_search.csv", index=False)
    (output_dir / "experiment_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    write_experiment_notes(comparison, protocol, output_dir)
    save_experiment_charts(forecasts, comparison, protocol, output_dir)
    print("\nPreliminary development comparison (final test not evaluated):")
    print(comparison[["method_name", "mae", "evaluated_weeks"]].to_string(index=False))
    print(f"SES alpha: {protocol['ses_alpha']:.2f}; results: {output_dir.resolve()}")
    return protocol
