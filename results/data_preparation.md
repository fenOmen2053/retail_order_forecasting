# Online Retail II data preparation

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
- Raw item rows: 1,067,371.
- Distinct eligible sales invoices over all source dates: 40,076.
- Complete calendar weeks: 104.
- Weeks containing source records: 102.
- Full-week date range: 2009-12-07 to 2011-12-04.
- Orders counted in observed complete weeks: 39,013.
- Weeks without source records (Monday dates): 2009-12-28, 2010-12-27.
- Empty weeks assumed zero in this run: False.
- Invoice identifiers with multiple timestamps: 82.
- Invoice identifiers spanning multiple calendar weeks: 0.

## Interpretation and limitations
The raw-row exclusion counts in the JSON report can overlap and must not be added together. Missing source weeks may represent a closure or incomplete data; the workbook alone does not establish the cause. Filtering cancellation records does not establish that every retained original sale was subsequently fulfilled or never returned. The invoice identifier is the operational definition of an order for this study. Source coverage at the boundaries is inferred from recorded dates rather than an independently verified trading calendar.

The four-week trailing mean on the exploratory chart includes the current week and is not a one-week-ahead forecast. The separate forecasting stage saves preliminary one-week-ahead results in the midterm subfolder. Its chronological evaluation protocol is documented there; the reserved final test is not evaluated.
