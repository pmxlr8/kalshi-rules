import argparse, json
import numpy as np
import pandas as pd
from config import DEFAULT_MODEL, RUNS, slug
from methods import evaluate_spec

def load(model_dir, evidence):
    rows = []
    for p in sorted((RUNS / slug(model_dir) / evidence).glob("*.jsonl")):
        rows += [json.loads(l) for l in p.open()]
    return pd.DataFrame(rows)

def bal_acc(g):
    pos, neg = g[g.gold == "YES"], g[g.gold == "NO"]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    return 0.5 * ((pos.verdict == "YES").mean() + (neg.verdict == "NO").mean())

def summary(df):
    g = df.groupby("method")
    out = pd.DataFrame({
        "n": g.size(), "acc": g.correct.mean(), "bal_acc": g.apply(bal_acc, include_groups=False),
        "abstain": g.verdict.apply(lambda v: (v == "ABSTAIN").mean()),
        "invalid": g.verdict.apply(lambda v: (v == "INVALID").mean()),
        "calls": g.calls.mean(), "tok_in": g.in_tok.mean(), "tok_out": g.out_tok.mean(),
    })
    return out.round(3)

def paired_diff(df, a, b, n_boot=2000, seed=0):
    x = df[df.method == a].set_index("item_id")
    y = df[df.method == b].set_index("item_id")
    common = x.index.intersection(y.index)
    d = (x.loc[common, "correct"].astype(float) - y.loc[common, "correct"].astype(float))
    ev = x.loc[common, "event"]
    per_ev = d.groupby(ev).agg(["sum", "size"])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(per_ev), size=(n_boot, len(per_ev)))
    s, n = per_ev["sum"].values, per_ev["size"].values
    boots = s[idx].sum(1) / n[idx].sum(1)
    return d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5), len(common)

def stage_table(df):
    s = df[df.spec.notna()].copy() if "spec" in df else pd.DataFrame()
    if s.empty:
        return s
    s["spec_ok"] = [float(evaluate_spec(sp, v) == g) if pd.notna(v) else np.nan for sp, v, g in zip(s.spec, s.value, s.gold)]
    s["value_ok"] = [float(pd.notna(pv) and pd.notna(v) and abs(float(pv) - float(v)) < 1e-6) for pv, v in zip(s.pred_value, s.value)]
    s["correct"] = s["correct"].astype(float)
    return s.groupby("method")[["spec_ok", "value_ok", "correct"]].mean().round(3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--evidence", default="report")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--ref", default="C2_cot")
    a = ap.parse_args()
    df = load(a.model, a.evidence)
    df = df[df.split == a.split]
    print("== overall\n", summary(df).to_string())
    for col in ["domain", "strike_type"]:
        print(f"\n== accuracy by {col}\n", df.pivot_table(index="method", columns=col, values="correct", aggfunc="mean").round(3).to_string())
    df["abs_margin_bin"] = pd.cut(df["margin_steps"].abs(), [-0.01, 0.5, 1, 2, 5, np.inf])
    print("\n== accuracy by |margin| in ladder steps\n", df.pivot_table(index="method", columns="abs_margin_bin", values="correct", aggfunc="mean", observed=False).round(3).to_string())
    print(f"\n== paired difference vs {a.ref} (95% CI, bootstrap by event)")
    for m in sorted(df.method.unique()):
        if m != a.ref:
            d, lo, hi, n = paired_diff(df, m, a.ref)
            print(f"  {m:24s} {d:+.3f}  [{lo:+.3f}, {hi:+.3f}]  n={n}")
    st = stage_table(df)
    if len(st):
        print("\n== structured pipeline stages (spec_ok: spec decides correctly on the gold value)\n", st.to_string())

if __name__ == "__main__":
    main()
