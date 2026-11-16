# Changelog

## 1.0.0

First release.

- Bootstraps a trade list into thousands of simulated paths and reports, per position size, the median and 5th-percentile final equity, probability of loss, probability of ruin, median and 95th-percentile maximum drawdown and the chance of drawdowns of chosen depths.
- Every size is evaluated on the same resampled paths, so sizes are compared fairly.
- Block bootstrap (`--block`) keeps winning and losing streaks together.
- Growth-optimal (Kelly) fraction from the sample, with a warning for sizes above it and for samples that are too good to trust.
- Seeded and reproducible; `--format json`.
