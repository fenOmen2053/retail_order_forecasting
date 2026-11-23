# Midterm forecasting experiment

These are preliminary development results. The reserved final test has not been evaluated.

## Methods

- Naive: forecast the last calendar week's observed count.
- MA4: forecast the mean of the four previous calendar weeks, excluding the target week.
- SES: initialize the level with the first observed training count; update it as alpha * observation + (1 - alpha) * previous level. The forecast is the latest level available before the target week.

## Protocol

- Initial training: 2009-12-07 to 2010-12-05 (52 calendar weeks).
- Development: 2010-12-06 to 2011-06-05 (26 calendar weeks).
- Reserved final test: 2011-06-06 to 2011-12-04 (26 calendar weeks).
- SES alpha: 0.70, selected using initial training SSE only and then held fixed.
- Training SSE is a parameter-fitting criterion, not the reported forecast accuracy.
- Development evaluation advances one week at a time. Earlier development observations may update forecasts for later weeks; future observations are never used.
- Missing weeks remain in the calendar. No zero or interpolated counts are invented. Naive and MA4 return unavailable forecasts when their required calendar history is missing. SES skips the update at a missing observation.
- MAE is the mean of abs(actual - prediction). All methods are compared on the same intersection of eligible weeks, with unrounded predictions.
- Common evaluated weeks: 21; excluded development weeks: 5.

## Preliminary comparison

| Method | MAE (orders) | Common evaluated weeks |
|---|---:|---:|
| Naive | 68.86 | 21 |
| Simple exponential smoothing | 74.14 | 21 |
| 4-week moving average | 83.46 | 21 |

Lowest development MAE: Naive.
This comparison is specific to the stated development dates and missing-data policy. It does not establish a universally best method. Inspect excluded weeks in development_forecasts.csv. The final test should be evaluated only after methods and preprocessing decisions are fixed.

## Sources

- [Forecast evaluation and time series cross-validation](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation)
- [Simple exponential smoothing](https://otexts.com/fpp3/exponential-smoothing.html#simple-exponential-smoothing)
