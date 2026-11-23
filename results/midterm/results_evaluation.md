# Preliminary Evaluation of Weekly Order Forecasts

The naive method achieved the lowest average error in this preliminary comparison of three methods for predicting the next week's order count in Online Retail II.

## Methods and formulas

Let $y_t$ be the observed number of orders in week $t$, and $\hat{y}_{t+1}$ the forecast for the following week.

### 1. Naive forecast

$$
\hat{y}_{t+1} = y_t
$$

The forecast equals the previous week's order count.

### 2. Four-week moving average

$$
\hat{y}_{t+1} = \frac{y_t + y_{t-1} + y_{t-2} + y_{t-3}}{4}
$$

The forecast is the average of the four previous calendar weeks. All four observations must be available; the target week is excluded.

### 3. Simple exponential smoothing

$$
\ell_t = \alpha y_t + (1-\alpha)\ell_{t-1},
\qquad \hat{y}_{t+1} = \ell_t
$$

Here, $\ell_t$ is the updated estimate of the order level. The first observed training value initializes this level. The selected $\alpha = 0.70$ gives the newest observation a weight of 70% and the previous level a weight of 30%. Alpha was selected from 0.05 to 1.00, in steps of 0.05, by minimizing training one-step squared errors, and then kept fixed.

## Evaluation procedure

- **Initial training:** 7 December 2009 to 5 December 2010, covering 52 calendar weeks.
- **Development evaluation:** 6 December 2010 to 5 June 2011, covering 26 calendar weeks.
- **Reserved final test:** 6 June to 4 December 2011, covering 26 weeks; not yet evaluated.

Forecasts were made one week at a time using only earlier observations. After each week, its observed value became available for the next forecast. Missing weeks remained missing. SES retained its level at a missing observation; naive and moving-average forecasts required their respective calendar history.

All methods were scored on the same **21 weeks**. Five development weeks were excluded: one had no actual observation, and four lacked complete four-week history.

Accuracy was measured by mean absolute error (MAE):

$$
\mathrm{MAE} = \frac{1}{n}\sum_{i=1}^{n}\left|y_i-\hat{y}_i\right|
$$

Here, $n=21$ is the number of evaluated weeks. MAE expresses the average size of the forecast error in orders; a lower value is better. Predictions were not rounded before evaluation.

## Results

| Method | MAE in orders | Evaluated weeks |
|---|---:|---:|
| Naive | **68.86** | 21 |
| Simple exponential smoothing | 74.14 | 21 |
| Four-week moving average | 83.46 | 21 |

## Interpretation and limitations

The naive forecast differed from the actual count by about 69 orders per evaluated week on average. Exponential smoothing and the four-week moving average had approximately 7.67% and 21.21% higher MAE, respectively. Smoothing therefore did not improve accuracy in this run.

These findings apply to this development period and the shared set of evaluated weeks. Excluding weeks with unavailable observations or history limits coverage. The results do not establish a universally best method; the reserved final test should be evaluated after the methodology is fixed.

## Sources

- Project results: [method comparison](method_comparison.csv), [individual forecasts](development_forecasts.csv), and [experiment protocol](experiment_protocol.json).
- Method references: [forecast evaluation](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation) and [simple exponential smoothing](https://otexts.com/fpp3/exponential-smoothing.html#simple-exponential-smoothing).
