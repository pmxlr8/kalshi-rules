import json, re
from datetime import datetime
import numpy as np
import pandas as pd
from config import RAW, PROC, WEATHER, ECON, FIN, domain_of

COMPARE = {
    "greater": lambda v, lo, hi: v > lo,
    "greater_or_equal": lambda v, lo, hi: v >= lo,
    "less": lambda v, lo, hi: v < hi,
    "less_or_equal": lambda v, lo, hi: v <= hi,
    "between": lambda v, lo, hi: lo <= v <= hi,
}

def num(x):
    if x is None or x == "":
        return None
    s = str(x).replace(",", "").replace("$", "").replace("%", "").replace("°", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

def margin(st, v, lo, hi):
    if v is None or st not in COMPARE:
        return None
    if st.startswith("greater"):
        return v - lo
    if st.startswith("less"):
        return hi - v
    return min(v - lo, hi - v)

def weather_fields(rules):
    st = re.search(r"\((CLI[A-Z]{3})\)", rules)
    dt = re.search(r"for ([A-Z][a-z]{2} \d{1,2}, \d{4})", rules)
    me = re.search(r"(maximum|minimum) temperature", rules)
    return {
        "station": st.group(1) if st else None,
        "obs_date": datetime.strptime(dt.group(1), "%b %d, %Y").date().isoformat() if dt else None,
        "measure": me.group(1) if me else None,
    }

def load(series):
    with open(RAW / "markets" / f"{series}.jsonl") as f:
        return [json.loads(l) for l in f]

def row(m, series):
    st = m.get("strike_type")
    lo, hi = m.get("floor_strike"), m.get("cap_strike")
    v = num(m.get("expiration_value"))
    gold_rule = None
    if st in COMPARE and v is not None:
        gold_rule = "yes" if COMPARE[st](v, lo, hi) else "no"
    rules = m.get("rules_primary") or ""
    r = {
        "item_id": m["ticker"], "series": series, "event": m["event_ticker"], "domain": domain_of(series),
        "title": m.get("title"), "yes_sub_title": m.get("yes_sub_title"),
        "rules_primary": rules, "rules_secondary": m.get("rules_secondary") or "",
        "strike_type": st, "floor": lo, "cap": hi,
        "expiration_value": m.get("expiration_value"), "value": v,
        "result": m.get("result"), "gold_rule": gold_rule,
        "close_time": m.get("close_time"), "last_price": num(m.get("last_price_dollars")),
        "volume": num(m.get("volume_fp")),
        "margin": margin(st, v, lo, hi),
        "strict_words": bool(re.search(r"strictly|greater than|above|more than|less than|below", rules, re.I)),
        "inclusive_words": bool(re.search(r"or above|or more|at least|or below|or less|at most|between", rules, re.I)),
        "rounding_clause": bool(re.search(r"decimal|rounded|round", rules, re.I)),
    }
    if r["domain"] == "weather":
        r.update(weather_fields(rules))
    return r

def main():
    rows = []
    for s in WEATHER + ECON + FIN:
        rows += [row(m, s) for m in load(s)]
    df = pd.DataFrame(rows)
    df = df[df["result"].isin(["yes", "no"])]
    steps = df.dropna(subset=["floor"]).groupby("event")["floor"].apply(
        lambda x: np.median(np.diff(np.sort(x.unique()))) if x.nunique() > 1 else np.nan)
    df["ladder_step"] = df["event"].map(steps)
    df["margin_steps"] = df["margin"] / df["ladder_step"]
    df.to_parquet(PROC / "items_all.parquet") if False else df.to_pickle(PROC / "items_all.pkl")
    chk = df.dropna(subset=["gold_rule"])
    print(f"items: {len(df)}  with numeric value + standard strike: {len(chk)}")
    print("result vs strike-rule agreement by series:")
    print(chk.assign(agree=chk.gold_rule == chk.result).groupby("series")["agree"].agg(["mean", "size"]).round(3).to_string())
    print("\nstrike types:\n", df.groupby(["domain", "strike_type"]).size().to_string())
    print("\nexpiration_value not numeric (sample):", df[df.value.isna()]["expiration_value"].dropna().unique()[:8])

if __name__ == "__main__":
    main()
