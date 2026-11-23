# References and Methodological Basis

The following sources support the theoretical background, data description, forecasting methods and evaluation procedure of the term paper on weekly order forecasting using public e-commerce data.

1. **Hyndman, R. J., & Athanasopoulos, G. (2021).** *Forecasting: Principles and Practice* (3rd ed.). OTexts. [Online edition](https://otexts.com/fpp3/).

   **Relevant parts:** Chapter 2, *Time series graphics*; Section 5.2, *Some simple forecasting methods*; Section 5.8, *Evaluating point forecast accuracy*; Section 5.10, *Time series cross-validation*; Section 8.1, *Simple exponential smoothing*.
   **Contribution:** Time-series concepts, graphical analysis, naive forecasting, SES, error measurement and chronological evaluation.

2. **NIST/SEMATECH. (n.d.).** *e-Handbook of Statistical Methods*. [Section 6.4.2.1](https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc421.htm); [Section 6.4.3.1](https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc431.htm).

   **Relevant parts:** *Single Moving Average* and *Single Exponential Smoothing*.
   **Contribution:** Definitions and mathematical formulation of moving averages and exponential smoothing. In this study, the trailing four-week average is used to forecast the following week.

3. **Gardner, E. S., Jr. (1985).** Exponential smoothing: The state of the art. *Journal of Forecasting, 4*(1), 1–28. [DOI](https://doi.org/10.1002/for.3980040103). [Author-hosted PDF](https://www.bauer.uh.edu/gardner/Exp-Sm-1985.pdf).

   **Relevant parts:** Introduction and discussion of simple exponential smoothing within the article on journal pages 1–28.
   **Contribution:** Theoretical background and established research on exponential smoothing.

4. **Hyndman, R. J., & Koehler, A. B. (2006).** Another look at measures of forecast accuracy. *International Journal of Forecasting, 22*(4), 679–688. [DOI](https://doi.org/10.1016/j.ijforecast.2006.03.001). [Author's publication page](https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/).

   **Relevant parts:** Introduction, discussion of scale-dependent, percentage and scaled error measures, and conclusions.
   **Contribution:** Assessment of forecast accuracy measures and their limitations. The paper's recommendation of MASE for comparing multiple series is distinguished from this study's use of MAE for one order-count series.

5. **Tashman, L. J. (2000).** Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting, 16*(4), 437–450. [DOI](https://doi.org/10.1016/S0169-2070(00)00065-0).

   **Relevant parts:** Section 2, *In-sample versus out-of-sample evaluation*; Section 3, *Fixed-origin versus rolling-origin procedures*; Section 4, *Issues in implementing out-of-sample evaluations*; Section 5 on method selection.
   **Contribution:** Chronological partitioning, sequential one-week-ahead evaluation and separation of preliminary method comparison from final testing.

6. **Fildes, R., Ma, S., & Kolassa, S. (2022).** Retail forecasting: Research and practice. *International Journal of Forecasting, 38*(4), 1283–1318. [DOI](https://doi.org/10.1016/j.ijforecast.2019.06.004). [University publication record](https://research.lancaster-university.uk/en/publications/retail-forecasting-research-and-practice/).

   **Relevant parts:** Introduction, discussion of retail forecasting tasks and comparative forecasting accuracy, and conclusions.
   **Contribution:** Retail business context, levels of aggregation and practical limitations. The study's target is order count; retail literature also considers other targets, including item sales and revenue.

7. **Makridakis, S., & Hibon, M. (2000).** The M3-Competition: Results, conclusions and implications. *International Journal of Forecasting, 16*(4), 451–476. [DOI](https://doi.org/10.1016/S0169-2070(00)00057-1).

   **Relevant parts:** *Introduction*, *The results of the M3-Competition*, and *Conclusions*.
   **Contribution:** Empirical comparison of forecasting methods and the role of simple benchmarks. The study's own results determine the ranking of its three methods.

8. **Chen, D. (2012).** *Online Retail II* [Dataset]. UCI Machine Learning Repository. [DOI](https://doi.org/10.24432/C5CG6D). [Dataset page](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii).

   **Relevant parts:** *Dataset Information*, *Additional Variable Information*, and *Citation*.
   **Contribution:** Data provenance, source coverage, variable definitions and dataset attribution. Data-cleaning rules are documented separately in the project's methodology.

9. **Shmueli, G., & Berger, E. (2025).** *Practical Time Series Forecasting with Python: A Hands-On Guide*. Axelrod Schnall Publishers. [Book website](https://www.forecastingbook.com/home). [Companion repository](https://github.com/gshmueli/ptsf-Python).

   **Relevant parts:** *Approaching Forecasting*, *Time Series Data*, *Performance Evaluation*, and *Smoothing Methods*.
   **Contribution:** Applied forecasting workflow, Python-based examples, performance evaluation and smoothing methods.

10. **Shmueli, G. (n.d.).** *Practical Time Series Forecasting: Accompanying videos* [Video collection]. [Author's website](https://www.forecastingbook.com/resources/videos).

    **Relevant parts:** *Data partitioning for time series*; *Naive forecasts*; *Predictive metrics & charts*; *Moving Average for visualization*; *Moving Average for forecasting*; *Simple exponential smoothing*.
    **Contribution:** Explanations of chronological evaluation, baseline forecasts and the distinction between historical smoothing and future forecasting.

11. **Penn State Department of Statistics. (n.d.).** *STAT 510: Applied Time Series Analysis*. [Lesson 5](https://online.stat.psu.edu/stat510/Lesson05).

    **Relevant parts:** Section 5.2, *Smoothing Time Series*, particularly *Moving Averages* and *Single Exponential Smoothing*.
    **Contribution:** Smoothing concepts and interpretation of time-series patterns. The forecasting procedure uses past observations only.

Online resources accessed on 5 November 2026. Section titles are provided where manuscript and published page numbering may differ.
