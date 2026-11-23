"""Prepare Online Retail II data and run the preliminary midterm experiment.

Run python main.py from the project directory.
The pipeline reads the source workbook and writes its outputs to results/.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from forecasting import run_midterm_experiment, validate_weekly_data


PROJECT_DIR = Path(__file__).resolve().parent


def load_data(input_path):
    """Read all worksheets and standardize their column names."""
    tables = []
    sheet_info = []
    invoice_sets = []
    aliases = {"InvoiceNo": "Invoice", "UnitPrice": "Price"}
    required = {"Invoice", "InvoiceDate", "Quantity", "Price"}

    with pd.ExcelFile(input_path, engine="openpyxl") as workbook:
        for sheet_name in workbook.sheet_names:
            print(f"Reading sheet: {sheet_name} ...", flush=True)
            table = pd.read_excel(workbook, sheet_name=sheet_name)
            table.columns = table.columns.astype(str).str.strip()
            table = table.rename(columns=aliases)
            missing = required - set(table.columns)
            if missing:
                raise ValueError(f"Sheet {sheet_name}: missing columns {sorted(missing)}")

            # Treat invoice numbers as identifiers even when Excel stores them as numbers.
            table["Invoice"] = (
                table["Invoice"].astype("string").str.strip()
                .str.replace(r"\.0$", "", regex=True).replace("", pd.NA)
            )
            table["InvoiceDate"] = pd.to_datetime(table["InvoiceDate"], errors="coerce")
            table["Quantity"] = pd.to_numeric(table["Quantity"], errors="coerce")
            table["Price"] = pd.to_numeric(table["Price"], errors="coerce")
            sheet_info.append({
                "sheet": sheet_name,
                "rows": len(table),
                "first_date": str(table["InvoiceDate"].min()),
                "last_date": str(table["InvoiceDate"].max()),
            })
            invoice_sets.append(set(table["Invoice"].dropna()))
            tables.append(table)
            print(f"  Loaded {len(table):,} rows.", flush=True)

    if not tables:
        raise ValueError("The workbook has no sheets.")
    overlaps = []
    for i in range(len(invoice_sets)):
        for j in range(i + 1, len(invoice_sets)):
            overlaps.append({
                "sheet_1": sheet_info[i]["sheet"],
                "sheet_2": sheet_info[j]["sheet"],
                "shared_invoice_ids": len(invoice_sets[i] & invoice_sets[j]),
            })
    return pd.concat(tables, ignore_index=True), sheet_info, overlaps


def prepare_weekly_orders(raw, assume_empty_weeks_zero=False):
    """Select eligible sales and count distinct invoices for each complete week."""
    valid_dates = raw["InvoiceDate"].dropna()
    if valid_dates.empty:
        raise ValueError("No valid invoice dates were found.")

    invoice = raw["Invoice"]
    cancellation = invoice.str.upper().str.startswith("C").fillna(False)
    numeric_invoice = invoice.str.fullmatch(r"\d+").fillna(False)
    valid_date = raw["InvoiceDate"].notna()

    # A sale requires a numeric invoice ID and at least one line with both
    # a positive quantity and a positive price. The count measures sales
    # invoices. The source data do not confirm delivery to customers.
    eligible = (
        numeric_invoice & valid_date
        & raw["Quantity"].gt(0) & raw["Price"].gt(0)
    ).fillna(False)
    sales = raw.loc[eligible, ["Invoice", "InvoiceDate"]]
    if sales.empty:
        raise ValueError("No sales matched the documented selection rules.")

    # An invoice can span several lines or appear on both worksheets.
    # Count it once using its earliest eligible timestamp.
    invoices = sales.groupby("Invoice")["InvoiceDate"].agg(
        first_timestamp="min", last_timestamp="max", timestamp_count="nunique"
    ).reset_index()
    conflicts = invoices.loc[invoices["timestamp_count"] > 1].copy()
    cross_week = (
        conflicts["first_timestamp"].dt.to_period("W-SUN")
        != conflicts["last_timestamp"].dt.to_period("W-SUN")
    )
    conflicts["crosses_week_boundary"] = cross_week
    invoices["week_start"] = invoices["first_timestamp"].dt.to_period("W-SUN").dt.start_time
    counts = invoices.groupby("week_start").size()

    # Drop partial weeks at the boundaries so that weekly counts are comparable.
    first_day = valid_dates.min().normalize()
    last_day = valid_dates.max().normalize()
    first_full_monday = first_day + pd.Timedelta(days=(-first_day.weekday()) % 7)
    last_full_monday = last_day - pd.Timedelta(days=last_day.weekday())
    if last_day.weekday() != 6:
        last_full_monday -= pd.Timedelta(days=7)
    calendar = pd.date_range(first_full_monday, last_full_monday, freq="W-MON")
    if calendar.empty:
        raise ValueError("The source does not cover a complete calendar week.")

    raw_weeks = raw.loc[valid_date, "InvoiceDate"].dt.to_period("W-SUN").dt.start_time
    raw_counts = raw_weeks.value_counts().reindex(calendar, fill_value=0)
    weekly = pd.DataFrame({"week_start": calendar})
    weekly["week_end"] = weekly["week_start"] + pd.Timedelta(days=6)
    weekly["raw_row_count"] = raw_counts.to_numpy()
    weekly["has_source_records"] = weekly["raw_row_count"] > 0
    weekly["order_count"] = counts.reindex(calendar, fill_value=0).to_numpy()

    # A week without source records has an unknown sales count.
    no_records = ~weekly["has_source_records"]
    weekly["order_count"] = weekly["order_count"].astype("Int64")
    if not assume_empty_weeks_zero:
        weekly.loc[no_records, "order_count"] = pd.NA
    weekly["is_assumed_zero"] = no_records & assume_empty_weeks_zero
    weekly = weekly[[
        "week_start", "week_end", "order_count", "raw_row_count",
        "has_source_records", "is_assumed_zero",
    ]]

    report = {
        "raw_rows": len(raw),
        "raw_unique_invoice_ids": int(invoice.nunique()),
        "missing_invoice_ids": int(invoice.isna().sum()),
        "invalid_or_missing_dates": int((~valid_date).sum()),
        "cancellation_rows": int(cancellation.sum()),
        "other_non_numeric_invoice_rows": int((invoice.notna() & ~numeric_invoice & ~cancellation).sum()),
        "nonpositive_quantity_rows": int(raw["Quantity"].le(0).sum()),
        "nonpositive_price_rows": int(raw["Price"].le(0).sum()),
        "eligible_sales_rows": int(eligible.sum()),
        "unique_sales_invoices_all_dates": len(invoices),
        "invoice_ids_with_multiple_timestamps": len(conflicts),
        "invoice_ids_crossing_week_boundaries": int(cross_week.sum()),
        "full_calendar_weeks": len(weekly),
        "observed_weeks": int(weekly["has_source_records"].sum()),
        "weeks_without_source_records": weekly.loc[no_records, "week_start"].dt.strftime("%Y-%m-%d").tolist(),
        "empty_weeks_assumed_zero": bool(assume_empty_weeks_zero),
        "counted_orders_in_observed_full_weeks": int(weekly.loc[~no_records, "order_count"].sum()),
        "first_full_week_start": str(first_full_monday.date()),
        "last_full_week_end": str((last_full_monday + pd.Timedelta(days=6)).date()),
        "source_first_date": str(valid_dates.min()),
        "source_last_date": str(valid_dates.max()),
    }
    return weekly, conflicts, report


def save_charts(weekly, output_dir):
    """Plot the observed weekly counts and their descriptive moving average."""
    import matplotlib

    matplotlib.use("Agg")  # Render plots to files without opening a window.
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    dates = weekly["week_start"]
    values = weekly["order_count"].astype(float)
    empty = weekly.loc[~weekly["has_source_records"], "week_start"]

    for smoothed in (False, True):
        fig, ax = plt.subplots(figsize=(12, 5.5))
        ax.plot(dates, values, color="#245A81", linewidth=1.5, label="Weekly orders")
        if smoothed:
            # Average four consecutive weeks only when all four counts are available.
            average = values.rolling(window=4, min_periods=4).mean()
            ax.plot(dates, average, color="#BD5B26", linewidth=2, label="4-week trailing mean")
        for i, date in enumerate(empty):
            ax.axvspan(date, date + pd.Timedelta(days=7), color="#929AA3", alpha=0.22,
                       label="No source records" if i == 0 else None)
        ax.set(title="Weekly order counts in Online Retail II",
               xlabel="Week beginning Monday", ylabel="Number of sales invoices")
        ax.set_ylim(bottom=0)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="upper left", frameon=False)
        note = ("Weeks without source records are assumed to have zero orders."
                if weekly["is_assumed_zero"].any()
                else "Weeks without source records remain missing; they are not set to zero.")
        fig.text(0.07, 0.02, note, fontsize=9, color="#505050")
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        name = "weekly_orders_smoothed.png" if smoothed else "weekly_orders.png"
        fig.savefig(output_dir / name, dpi=180)
        plt.close(fig)


def write_methodology(report, output_dir):
    """Record the processing rules and limitations for the report."""
    missing_weeks = ", ".join(report["weeks_without_source_records"]) or "None"
    text = f"""# Online Retail II data preparation

## Research variable
The target is the weekly count of distinct sales invoice identifiers across all countries in the supplied workbook. It is not item quantity, revenue, or a verified count of fulfilled customer orders.

## Preparation rules
1. Read all workbook sheets and combine their records.
2. Retain rows with a numeric invoice identifier, a valid date, quantity greater than zero, and price greater than zero. Cancellation documents and other nonnumeric identifiers are excluded.
3. Count each eligible invoice identifier once across the entire workbook. Exact duplicate item rows cannot increase this invoice count.
4. Assign each invoice to its earliest eligible timestamp. Multiple timestamps are listed separately in invoice_date_conflicts.csv when present.
5. Aggregate by calendar weeks running from Monday through Sunday. Use dates as recorded in the source; no timezone conversion is applied.
6. Exclude incomplete boundary weeks, using the first and last dates recorded in the source as coverage boundaries.
7. Preserve weeks without any source records in the calendar. Their counts are left missing by default. A zero can be assigned only using the explicit command-line assumption.
8. Customer identifiers and product descriptions are not required for eligibility.

## Observed results
- Raw item rows: {report['raw_rows']:,}.
- Distinct eligible sales invoices over all source dates: {report['unique_sales_invoices_all_dates']:,}.
- Complete calendar weeks: {report['full_calendar_weeks']}.
- Weeks containing source records: {report['observed_weeks']}.
- Full-week date range: {report['first_full_week_start']} to {report['last_full_week_end']}.
- Orders counted in observed complete weeks: {report['counted_orders_in_observed_full_weeks']:,}.
- Weeks without source records (Monday dates): {missing_weeks}.
- Empty weeks assumed zero in this run: {report['empty_weeks_assumed_zero']}.
- Invoice identifiers with multiple timestamps: {report['invoice_ids_with_multiple_timestamps']}.
- Invoice identifiers spanning multiple calendar weeks: {report['invoice_ids_crossing_week_boundaries']}.

## Interpretation and limitations
The raw-row exclusion counts in the JSON report can overlap and must not be added together. Missing source weeks may represent a closure or incomplete data; the workbook alone does not establish the cause. Filtering cancellation records does not establish that every retained original sale was subsequently fulfilled or never returned. The invoice identifier is the operational definition of an order for this study. Source coverage at the boundaries is inferred from recorded dates rather than an independently verified trading calendar.

The four-week trailing mean on the exploratory chart includes the current week and is not a one-week-ahead forecast. The separate forecasting stage saves preliminary one-week-ahead results in the midterm subfolder. Its chronological evaluation protocol is documented there; the reserved final test is not evaluated.
"""
    (output_dir / "data_preparation.md").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Prepare weekly orders from Online Retail II.")
    parser.add_argument("--input", type=Path, default=PROJECT_DIR / "data" / "online_retail_II.xlsx")
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "results")
    parser.add_argument("--from-weekly", type=Path,
                        help="Reuse an existing prepared weekly CSV instead of reading Excel again.")
    parser.add_argument("--train-weeks", type=int, default=52)
    parser.add_argument("--holdout-weeks", type=int, default=26)
    parser.add_argument("--assume-empty-weeks-zero", action="store_true",
                        help="Explicitly assume that weeks without source records had zero orders.")
    args = parser.parse_args()
    if args.from_weekly:
        if args.assume_empty_weeks_zero:
            parser.error("Do not combine --from-weekly with a new missing-week assumption. Rebuild from Excel to change preprocessing.")
        print(f"Using prepared CSV: {args.from_weekly}. Raw Excel is not reprocessed.")
        weekly = validate_weekly_data(pd.read_csv(args.from_weekly))
        run_midterm_experiment(weekly, args.output / "midterm", args.train_weeks, args.holdout_weeks)
        return
    if not args.input.is_file():
        parser.error(f"Dataset not found: {args.input}\nPlace online_retail_II.xlsx in the data folder.")

    raw, sheets, overlaps = load_data(args.input)
    print("Preparing weekly orders ...", flush=True)
    weekly, conflicts, report = prepare_weekly_orders(raw, args.assume_empty_weeks_zero)
    report.update({
        "source_file": args.input.name,
        "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "sheets": sheets,
        "sheet_invoice_overlaps": overlaps,
    })
    args.output.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(args.output / "weekly_orders.csv", index=False, date_format="%Y-%m-%d")
    # Write column headers even when there are no conflicts. This replaces
    # any conflict report left over from a run on a different dataset.
    conflicts.to_csv(args.output / "invoice_date_conflicts.csv", index=False)
    (args.output / "data_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_methodology(report, args.output)
    save_charts(weekly, args.output)

    print(f"\nDone. Results: {args.output.resolve()}")
    print(f"Raw rows: {report['raw_rows']:,}")
    print(f"Full calendar weeks: {report['full_calendar_weeks']}")
    print(f"Weeks with source records: {report['observed_weeks']}")
    print(f"Orders in observed full weeks: {report['counted_orders_in_observed_full_weeks']:,}")
    if report["weeks_without_source_records"]:
        print("Weeks without source records: " + ", ".join(report["weeks_without_source_records"]))
    if report["invoice_ids_crossing_week_boundaries"]:
        print("WARNING: Some invoice IDs span multiple weeks. Review invoice_date_conflicts.csv.")
    run_midterm_experiment(weekly, args.output / "midterm", args.train_weeks, args.holdout_weeks)


if __name__ == "__main__":
    main()
