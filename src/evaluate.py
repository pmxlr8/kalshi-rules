import argparse, json, re
import numpy as np
import pandas as pd
from config import DEFAULT_MODEL, RUNS, slug
from methods import evaluate_spec, normalize_spec

VERDICT_WORD = re.compile(r"verdict(?:\s+(?:is|would be|should be))?\W{0,15}(yes|no|abstain)\b", re.I)
SPEC_METHODS = {"C4_spec_code", "O1_C4_gold_spec", "O2_C4_gold_value"}

def lenient_verdict(raw):
    """Last 'verdict ... YES/NO/ABSTAIN' in free text, for answers that skip the JSON format."""
    m = VERDICT_WORD.findall(raw or "")
    return m[-1].upper() if m else "INVALID"

def add_tolerant(df, model=None, evidence=None):
    """Second, format-tolerant score for every row (no new LLM calls):
    free-text methods: an INVALID answer is re-read with lenient_verdict;
    spec methods: the saved spec is re-read with normalize_spec (comparator words, bounds in the wrong field),
    and a value lost to cut-off extractor JSON is read from the cached text (replay.py).
    The gap correct_tol - correct is the share of errors that are only format slips."""
    vt, vals = [], []
    for i, m, v, raw, sp, pv in zip(df.item_id, df.method, df.verdict, df.raw, df.get("spec", [None] * len(df)), df.get("pred_value", [None] * len(df))):
        pv = None if pv is None or pd.isna(pv) else float(pv)
        if m in SPEC_METHODS and pv is None and model and m != "O2_C4_gold_value":
            from replay import tolerant_value  # cut-off extractor JSON: read the value it already wrote
            pv = tolerant_value(model, i, m, evidence)
        vals.append(pv)
        if m in SPEC_METHODS:
            vt.append(evaluate_spec(normalize_spec(sp), pv))
        elif v == "INVALID" and not str(m).startswith("C3"):
            vt.append(lenient_verdict(raw))
        else:
            vt.append(v)
    df = df.copy()
    df["verdict_tol"], df["pred_value_tol"] = vt, vals
    df["correct_tol"] = df.verdict_tol == df.gold
    return df

def tolerant_view(df):
    """The same rows, scored with the tolerant reading (for paired tests and slices)."""
    d = df.copy()
    d["verdict"], d["correct"] = d.verdict_tol, d.correct_tol
    return d

def load(model_dir, evidence, derived=True):
    rows = []
    for p in sorted((RUNS / slug(model_dir) / evidence).glob("*.jsonl")):
        rows += [json.loads(l) for l in p.open()]
    df = pd.DataFrame(rows)
    return add_tolerant(df, model_dir, evidence) if derived and len(df) else df

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
