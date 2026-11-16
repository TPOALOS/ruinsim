"""Bootstrap risk simulation over a trade list (standard library only)."""
import csv
import math
import random

MIN_TRADES = 30
RETURN_COLS = ("ret", "return", "pnl_pct", "r", "pnl", "trade_return")


def load(path, col=None):
    """Read per-trade returns as fractions of the capital deployed (0.02 = +2%)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)
    low = {h.strip().lower(): h for h in header}
    if col is None:
        for name in RETURN_COLS:
            if name in low:
                col = low[name]
                break
        if col is None:
            raise ValueError("%s: no return column found; pass --col (columns: %s)" % (path, ", ".join(header)))
    elif col not in header:
        raise ValueError("%s: column %r not found (columns: %s)" % (path, col, ", ".join(header)))
    out = []
    for i, row in enumerate(rows, 2):
        raw = (row[col] or "").strip()
        pct = raw.endswith("%")
        try:
            v = float(raw.rstrip("%"))
        except ValueError:
            raise ValueError("%s line %d: %r is not a number" % (path, i, row[col]))
        if not math.isfinite(v):
            raise ValueError("%s line %d: non-finite value" % (path, i))
        v = v / 100.0 if pct else v
        if v <= -1.0:
            raise ValueError("%s line %d: a return of %g loses more than the whole stake; give returns as fractions" % (path, i, v))
        out.append(v)
    if len(out) < MIN_TRADES:
        raise ValueError("%s: need at least %d trades (got %d)" % (path, MIN_TRADES, len(out)))
    return out


def percentile(sorted_vals, q):
    k = (len(sorted_vals) - 1) * q
    lo = int(math.floor(k))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def kelly(returns, step=0.01, f_max=5.0):
    """Fraction of equity per trade that maximises mean log growth over the sample; (f, growth per trade)."""
    best_f, best_g = 0.0, 0.0
    f = step
    while f <= f_max + 1e-9:
        if all(1 + f * r > 0 for r in returns):
            g = sum(math.log(1 + f * r) for r in returns) / len(returns)
            if g > best_g:
                best_f, best_g = f, g
        else:
            break
        f += step
    return best_f, best_g


def make_paths(returns, horizon, paths, block, rng):
    n = len(returns)
    out = []
    for _ in range(paths):
        p = []
        while len(p) < horizon:
            s = rng.randrange(n)
            for j in range(block):
                p.append(returns[(s + j) % n])
                if len(p) == horizon:
                    break
        out.append(p)
    return out


def run_size(paths, f, ruin, dd_levels):
    finals, maxdds = [], []
    ruined = 0
    for p in paths:
        eq = peak = 1.0
        mdd = 0.0
        hit = False
        for r in p:
            g = 1.0 + f * r
            eq = eq * g if g > 0 else 0.0
            if eq > peak:
                peak = eq
            dd = 1.0 - eq / peak
            if dd > mdd:
                mdd = dd
            if eq <= ruin:
                hit = True
            if eq == 0.0:
                break
        finals.append(eq)
        maxdds.append(mdd)
        ruined += hit
    n = len(paths)
    sf, sd = sorted(finals), sorted(maxdds)
    return {
        "f": f, "median_final": percentile(sf, 0.5), "p5_final": percentile(sf, 0.05), "p95_final": percentile(sf, 0.95),
        "p_loss": sum(1 for x in finals if x < 1.0) / n, "p_ruin": ruined / n,
        "median_max_dd": percentile(sd, 0.5), "p95_max_dd": percentile(sd, 0.95),
        "p_dd": {("%g" % lv): sum(1 for x in maxdds if x >= lv) / n for lv in dd_levels},
    }


def simulate(returns, sizes, horizon=250, paths=2000, block=1, ruin=0.5, dd_levels=(0.2, 0.3, 0.5), seed=1):
    rng = random.Random(seed)
    pts = make_paths(returns, horizon, paths, block, rng)
    kf, kg = kelly(returns)
    n = len(returns)
    m = sum(returns) / n
    wins = sum(1 for r in returns if r > 0)
    return {
        "trades": n, "mean_return": m, "win_rate": wins / n, "worst_trade": min(returns), "best_trade": max(returns),
        "kelly_fraction": kf, "kelly_capped": kf >= 5.0 - 1e-9, "kelly_growth_per_trade": kg, "horizon": horizon, "paths": paths, "block": block, "ruin_level": ruin,
        "sizes": [run_size(pts, f, ruin, dd_levels) for f in sizes],
    }
