import numpy as np
import pandas as pd
from config import PROC
from evidence import weather_report

SEED = 7

def split_events(events, dev_frac, rng):
    ev = np.array(sorted(events))
    rng.shuffle(ev)
    n_dev = int(round(len(ev) * dev_frac))
    return set(ev[:n_dev])

def main(days_per_series=8, fin_events=12, per_event=6, dev_frac=0.25):
    rng = np.random.default_rng(SEED)
    df = pd.read_parquet(PROC / "items_all.parquet")
    df = df[df.gold_rule.notna() & (df.gold_rule == df.result)]

    w = df[df.domain == "weather"].copy()
    w["has_report"] = w.apply(lambda r: weather_report(r)[1] is not None, axis=1)
    w = w[w.has_report]
    picked = []
    for s, g in w.groupby("series"):
        evs = sorted(g.event.unique())
        picked += list(rng.choice(evs, size=min(days_per_series, len(evs)), replace=False))
    w = w[w.event.isin(picked)]

    f = df[df.domain == "fin"]
    f = f[f.series.isin(["KXINX", "KXAAAGASD", "KXAAAGASW", "KXINXU"])]
    fevs = []
    for s, g in f.groupby("series"):
        evs = sorted(g.event.unique())
        fevs += list(rng.choice(evs, size=min(fin_events // 2, len(evs)), replace=False))
    f = f[f.event.isin(fevs)]
    f = f.sample(frac=1, random_state=SEED).groupby("event").head(per_event)

    e = df[df.domain == "econ"]
    e = e.sample(frac=1, random_state=SEED).groupby("event").head(per_event * 2)

    items = pd.concat([w, f, e])
    dev = split_events(items.event.unique(), dev_frac, rng)
    items["split"] = np.where(items.event.isin(dev), "dev", "test")
    items = items.drop(columns=["has_report"], errors="ignore").reset_index(drop=True)
    items.to_parquet(PROC / "items_study.parquet", index=False, compression="zstd")
    print(items.groupby(["domain", "split"]).agg(items=("item_id", "size"), events=("event", "nunique")).to_string())
    print("\nYES rate by domain:", items.assign(y=items.result == "yes").groupby("domain")["y"].mean().round(2).to_dict())

if __name__ == "__main__":
    main()
