import pandas as pd
from config import PROC
from evidence import weather_report

df = pd.read_pickle(PROC / "items_all.pkl")
w = df[df.domain == "weather"].drop_duplicates(["station", "obs_date", "measure"])
bad, miss = 0, 0
for _, r in w.iterrows():
    _, prod = weather_report(r)
    if prod is None:
        miss += 1
        continue
    got = prod["max"] if r["measure"] == "maximum" else prod["min"]
    try:
        if float(got) != float(r["value"]):
            bad += 1
    except (TypeError, ValueError):
        bad += 1
print(f"station-days: {len(w)}  missing report: {miss}  report value != Kalshi value: {bad}")
