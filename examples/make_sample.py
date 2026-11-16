"""Write trades.csv: 150 trades, 52% win rate, winners +3%, losers -3%, plus two -12% disasters."""
import random

rng = random.Random(8)
with open("trades.csv", "w") as fh:
    fh.write("ret\n")
    for i in range(150):
        r = 0.03 if rng.random() < 0.52 else -0.03
        if i in (37, 90):
            r = -0.12
        fh.write("%.4f\n" % r)
