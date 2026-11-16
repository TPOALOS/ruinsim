# ruinsim

[![tests](https://github.com/TPOALOS/ruinsim/actions/workflows/tests.yml/badge.svg)](https://github.com/TPOALOS/ruinsim/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

**How big can you trade before the drawdown kills you?** A backtest shows one path. `ruinsim` resamples your own trade list into thousands of alternative
histories and shows, for each **position size**, how deep the drawdowns get, how often you lose money, and how often you hit your personal ruin level.

Pure Python standard library: no pandas, no numpy, no install step.

```bash
python3 examples/make_sample.py
python3 -m ruinsim examples/trades.csv --sizes 0.25,0.5,1,2
```

```
  size   median final  p5 final   P(loss)  P(ruin)  med maxDD  p95 maxDD  P(DD>=20%)  P(DD>=30%)  P(DD>=50%)
  0.25         1.34x     1.07x        2%       0%         7%        14%          0%          0%          0%
  0.5          1.76x     1.12x        2%       0%        15%        26%         18%          2%          0%
  1            2.88x     1.16x        2%       1%        28%        47%         87%         43%          3%
  2            6.19x     1.02x        5%      11%        52%        75%        100%         98%         54%

Growth-optimal (Kelly) size on this sample: 3.88 of equity per trade; half-Kelly is 1.94.
```

The same trades give a median 6x at size 2 and a 98% chance of a 30% drawdown on the way. Whether that is acceptable is your decision; `ruinsim` makes the price visible.

## Input

A CSV with one row per trade and a return column. The return is the profit or loss as a **fraction of the capital deployed in that trade**
(0.02 = +2%, `2%` also works). Column is auto-detected from `ret`, `return`, `pnl_pct`, `r`, `pnl`, `trade_return`, or pass `--col`.
A **size** is the fraction of your equity put into each trade: size 0.5 turns a +4% trade into +2% of equity.

## Options

```bash
python3 -m ruinsim FILE [--col ret] [--sizes 0.1,0.25,0.5,1] [--horizon 250] [--paths 2000] [--block 1]
                        [--ruin 0.5] [--dd 0.2,0.3,0.5] [--seed 1] [--format text|json]
```

- `--horizon`: how many trades each simulated future contains.
- `--ruin`: equity level you call ruin, as a fraction of the start (0.5 = down half). A path that ever touches it counts.
- `--block N`: resample N consecutive trades at a time, so streaks stay together. Compare with the default to see how much clustering matters.

## How it works

Each path draws `--horizon` trades with replacement from your list. For size *f*, equity multiplies by `1 + f x return` each trade (floored at zero), and the
maximum drawdown is tracked from the running peak. Every size is evaluated on the **same** resampled paths, so differences between rows come from size alone.
Kelly is the *f* that maximises the sample's mean log growth.

## Limits

- It only knows the trades you give it. A strategy that has not yet met its worst market will look safer than it is; worst-case losses larger than the sample's worst are possible.
- With the default `--block 1`, trades are independent. Real losses cluster, so also run with `--block 5` or more.
- Kelly estimated from a sample is biased upwards; do not size at full Kelly.
- Costs, slippage and leverage limits are whatever is already in your trade returns; none are added here.
- Not financial advice.

## Tests

```bash
python3 -m unittest -v
```

MIT licensed.
