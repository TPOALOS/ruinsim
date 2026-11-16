"""Command line interface."""
import argparse
import json
import sys

from . import DISCLAIMER, __version__, core


def build_parser():
    ap = argparse.ArgumentParser(prog="ruinsim", description="Bootstrap your trades: drawdown and ruin risk at different position sizes.")
    ap.add_argument("--version", action="version", version="ruinsim " + __version__)
    ap.add_argument("file", help="CSV with one row per trade")
    ap.add_argument("--col", help="return column (default: first of ret, return, pnl_pct, r, pnl, trade_return)")
    ap.add_argument("--sizes", default="0.1,0.25,0.5,1.0", help="fractions of equity risked per trade, comma separated")
    ap.add_argument("--horizon", type=int, default=250, help="trades per simulated path (default 250)")
    ap.add_argument("--paths", type=int, default=2000)
    ap.add_argument("--block", type=int, default=1, help="block length for the bootstrap; >1 keeps winning/losing streaks together (default 1)")
    ap.add_argument("--ruin", type=float, default=0.5, help="equity level counted as ruin, as a fraction of the start (default 0.5)")
    ap.add_argument("--dd", default="0.2,0.3,0.5", help="drawdown levels to report probabilities for")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    return ap


def _floats(text, name):
    try:
        vals = [float(x) for x in text.split(",")]
    except ValueError:
        raise ValueError("%s must be comma-separated numbers" % name)
    if not vals or any(v <= 0 for v in vals):
        raise ValueError("%s must be positive" % name)
    return vals


def render(r):
    L = ["%d trades: mean %+.2f%%, win rate %.0f%%, best %+.1f%%, worst %+.1f%%" % (
        r["trades"], r["mean_return"] * 100, r["win_rate"] * 100, r["best_trade"] * 100, r["worst_trade"] * 100),
        "%d paths x %d trades, block %d, ruin = equity at or below %.0f%% of the start" % (
            r["paths"], r["horizon"], r["block"], r["ruin_level"] * 100), ""]
    dd_keys = list(r["sizes"][0]["p_dd"].keys())
    head = "  size   median final  p5 final   P(loss)  P(ruin)  med maxDD  p95 maxDD  " + "  ".join("P(DD>=%s%%)" % ("%g" % (float(k) * 100)) for k in dd_keys)
    L.append(head)
    for s in r["sizes"]:
        L.append("  %-5g  %10.2fx  %7.2fx  %7.0f%%  %6.0f%%  %8.0f%%  %8.0f%%  " % (
            s["f"], s["median_final"], s["p5_final"], s["p_loss"] * 100, s["p_ruin"] * 100, s["median_max_dd"] * 100, s["p95_max_dd"] * 100)
            + "  ".join("%9.0f%%" % (s["p_dd"][k] * 100) for k in dd_keys))
    L.append("")
    if r["kelly_fraction"] > 0:
        if r["kelly_capped"]:
            L.append("Growth-optimal (Kelly) size is above 5x equity on this sample: the trades are too good to be a reliable guide (or too few).")
        else:
            L.append("Growth-optimal (Kelly) size on this sample: %.2f of equity per trade; half-Kelly is %.2f." % (r["kelly_fraction"], r["kelly_fraction"] / 2))
        over = [s["f"] for s in r["sizes"] if s["f"] > r["kelly_fraction"]]
        if over:
            L.append("  Sizes above Kelly (%s) have LOWER expected growth and more risk than a smaller size." % ", ".join("%g" % x for x in over))
    else:
        L.append("No positive position size has positive log growth on this sample: the trades lose money when compounded.")
    L.append("Kelly from a sample is an overestimate of the truth; treat half-Kelly as an upper bound, not a target.")
    return "\n".join(L)


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        sizes = _floats(a.sizes, "--sizes")
        dd = _floats(a.dd, "--dd")
        if a.horizon < 1 or a.paths < 100 or a.block < 1:
            raise ValueError("--horizon >= 1, --paths >= 100 and --block >= 1 are required")
        if not 0 < a.ruin < 1:
            raise ValueError("--ruin must be between 0 and 1")
        rets = core.load(a.file, a.col)
        res = core.simulate(rets, sizes, a.horizon, a.paths, a.block, a.ruin, dd, a.seed)
    except (ValueError, OSError) as exc:
        print("ruinsim: error: %s" % exc, file=sys.stderr)
        return 2
    if a.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print(render(res))
        print("")
        print("Trades are resampled as independent (use --block to keep streaks together); real losses can cluster harder than the sample.")
        print(DISCLAIMER)
    return 0
