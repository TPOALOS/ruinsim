import contextlib
import io
import json
import os
import random
import tempfile
import unittest

from ruinsim import cli, core


def write(path, rets, header="ret"):
    with open(path, "w") as fh:
        fh.write(header + "\n")
        for r in rets:
            fh.write("%s\n" % r)


def run_cli(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(args)
    return code, out.getvalue(), err.getvalue()


class SimTests(unittest.TestCase):
    def test_all_winners_never_lose_or_ruin(self):
        r = core.simulate([0.01] * 40, [0.5, 1.0], horizon=100, paths=200)
        for s in r["sizes"]:
            self.assertEqual(s["p_loss"], 0.0)
            self.assertEqual(s["p_ruin"], 0.0)
            self.assertEqual(s["median_max_dd"], 0.0)

    def test_zero_size_keeps_equity(self):
        r = core.simulate([0.02, -0.01] * 20, [1e-12], horizon=50, paths=200)
        self.assertAlmostEqual(r["sizes"][0]["median_final"], 1.0, places=6)

    def test_all_losers_hit_ruin(self):
        r = core.simulate([-0.5] * 40, [1.0], horizon=10, paths=200, ruin=0.5)
        self.assertEqual(r["sizes"][0]["p_ruin"], 1.0)
        self.assertEqual(r["kelly_fraction"], 0.0)

    def test_total_wipeout_floors_at_zero(self):
        s = core.run_size([[-0.99, 0.5, 0.5]], 2.0, 0.5, [0.5])  # 1 - 1.98 < 0
        self.assertEqual(s["median_final"], 0.0)
        self.assertEqual(s["p_ruin"], 1.0)
        self.assertEqual(s["median_max_dd"], 1.0)

    def test_kelly_matches_closed_form(self):
        f, g = core.kelly([1.0, -0.5] * 20, step=0.01)
        self.assertAlmostEqual(f, 0.5, delta=0.011)
        self.assertGreater(g, 0)

    def test_kelly_zero_for_negative_edge(self):
        self.assertEqual(core.kelly([0.01, -0.02] * 20)[0], 0.0)

    def test_seed_reproducible_and_different_seeds_differ(self):
        rng = random.Random(1)
        rets = [rng.gauss(0.002, 0.02) for _ in range(60)]
        a = core.simulate(rets, [0.5], 100, 300, seed=5)
        b = core.simulate(rets, [0.5], 100, 300, seed=5)
        c = core.simulate(rets, [0.5], 100, 300, seed=6)
        self.assertEqual(a, b)
        self.assertNotEqual(a["sizes"], c["sizes"])

    def test_bigger_size_means_deeper_drawdowns(self):
        rng = random.Random(2)
        rets = [rng.gauss(0.003, 0.02) for _ in range(100)]
        r = core.simulate(rets, [0.25, 1.0, 2.0], 250, 800)
        dd = [s["median_max_dd"] for s in r["sizes"]]
        self.assertEqual(dd, sorted(dd))

    def test_block_bootstrap_keeps_whole_sequence(self):
        rets = [-0.1] * 15 + [0.1] * 15  # 30 trades
        paths = core.make_paths(rets, 30, 50, 30, random.Random(1))
        for p in paths:
            self.assertEqual(sorted(p), sorted(rets))  # each path is a rotation of the full list

    def test_blocks_raise_drawdown_for_streaky_trades(self):
        rets = [-0.05] * 10 + [0.05] * 10 + [-0.05] * 5 + [0.05] * 15
        iid = core.simulate(rets, [1.0], 40, 1500, block=1)["sizes"][0]["p95_max_dd"]
        blk = core.simulate(rets, [1.0], 40, 1500, block=10)["sizes"][0]["p95_max_dd"]
        self.assertGreater(blk, iid)

    def test_path_length_exact(self):
        paths = core.make_paths([0.1] * 30, 25, 10, 7, random.Random(1))
        self.assertTrue(all(len(p) == 25 for p in paths))


class LoadAndCliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "t.csv")

    def test_percent_values_and_column_detection(self):
        write(self.path, ["2%", "-1%"] * 20, header="pnl_pct")
        r = core.load(self.path)
        self.assertEqual(r[:2], [0.02, -0.01])

    def test_explicit_col(self):
        with open(self.path, "w") as fh:
            fh.write("a,b\n" + "0.01,0.02\n" * 40)
        self.assertEqual(core.load(self.path, "b")[0], 0.02)

    def test_load_errors(self):
        write(self.path, [0.01] * 10)
        with self.assertRaises(ValueError):
            core.load(self.path)  # too few
        write(self.path, [0.01] * 40, header="x")
        with self.assertRaises(ValueError):
            core.load(self.path)  # no return column
        write(self.path, [0.01] * 39 + ["abc"])
        with self.assertRaises(ValueError):
            core.load(self.path)
        write(self.path, [0.01] * 39 + [-1.5])
        with self.assertRaises(ValueError):
            core.load(self.path)

    def test_cli_text_and_json(self):
        rng = random.Random(3)
        write(self.path, ["%.4f" % rng.gauss(0.004, 0.02) for _ in range(80)])
        code, out, _ = run_cli([self.path, "--paths", "300", "--horizon", "100"])
        self.assertEqual(code, 0)
        self.assertIn("Kelly", out)
        code, out, _ = run_cli([self.path, "--paths", "300", "--format", "json", "--sizes", "0.5,1"])
        self.assertEqual(len(json.loads(out)["sizes"]), 2)

    def test_cli_errors(self):
        write(self.path, [0.01] * 40)
        for bad in (["--sizes", "a"], ["--sizes", "0"], ["--paths", "5"], ["--ruin", "1.5"], ["--horizon", "0"], ["--col", "zzz"]):
            self.assertEqual(run_cli([self.path] + bad)[0], 2, bad)
        self.assertEqual(run_cli([self.path + ".x"])[0], 2)


if __name__ == "__main__":
    unittest.main()
