import argparse, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import DEFAULT_MODEL, ROOT, PROC, slug
from evaluate import load, summary, paired_diff, stage_table
from methods import evaluate_spec

warnings.filterwarnings("ignore")
ORDER = ["B1_no_evidence", "B2_no_rules", "C1_direct", "C2_cot", "C2SC_cot_vote5", "C3_spec_prose", "C4_spec_code",
         "O1_C4_gold_spec", "O2_C4_gold_value", "O3_C2_gold_spec_text"]
COLORS = {"C1_direct": "#2a78d6", "C2_cot": "#eb6834", "C2SC_cot_vote5": "#1baf7a", "C3_spec_prose": "#eda100",
          "C4_spec_code": "#e87ba4"}

def with_features(df):
    feat = pd.read_pickle(PROC / "items_study_feat.pkl")[["item_id", "near", "distractor_flip", "abs_departure", "rounding_clause"]]
    df = df.merge(feat, on="item_id", how="left")
    if "B1_no_evidence" in set(df.method):
        b1 = df[df.method == "B1_no_evidence"].set_index("item_id")["correct"]
        df["prior_conflict"] = ~df["item_id"].map(b1).fillna(True).astype(bool)
    return df

def gain_by(df, a, b, col):
    rows = []
    for k, g in df.groupby(col):
        if not {a, b} <= set(g.method):
            continue
        d, lo, hi, n = paired_diff(g, a, b)
        rows.append({col: k, "n": n, f"acc_{b}": g[g.method == b].correct.mean(), f"acc_{a}": g[g.method == a].correct.mean(),
                     "gain": d, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows).round(3)

def error_budget(df):
    s = df[df.method.isin(["C3_spec_prose", "C4_spec_code"]) & ~df.correct.astype(bool)].copy()
    if s.empty:
        return s
    s["spec_wrong"] = [evaluate_spec(sp, v) != g if pd.notna(v) else np.nan for sp, v, g in zip(s.spec, s.value, s.gold)]
    s["value_wrong"] = [not (pd.notna(pv) and abs(float(pv) - float(v)) < 1e-6) for pv, v in zip(s.pred_value, s.value)]
    s["stage"] = np.select([s.spec_wrong & s.value_wrong, s.spec_wrong, s.value_wrong], ["spec+value", "spec", "value"], "apply")
    return s.groupby(["method", "stage"]).size().unstack(fill_value=0)

def regression(df, a="C4_spec_code", b="C2_cot"):
    try:
        import statsmodels.formula.api as smf
        d = df[df.method.isin([a, b])].copy()
        d["structured"] = (d.method == a).astype(int)
        d["y"] = d.correct.astype(int)
        d["near"] = d["near"].astype(int); d["distractor_flip"] = d["distractor_flip"].astype(int)
        m = smf.glm("y ~ structured * (near + distractor_flip + C(domain))", d,
                    family=__import__("statsmodels.api").api.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(d.event)[0]})
        return m.summary2().tables[1][["Coef.", "Std.Err.", "P>|z|"]].round(3)
    except Exception as e:
        return pd.DataFrame({"note": [f"regression not estimable: {type(e).__name__}: {e}"[:200]]})

def router(dev, test, cands=("C2_cot", "C4_spec_code"), keys=("domain", "strike_type", "near")):
    keys = list(keys)
    dv = dev[dev.method.isin(cands)]
    cost = dv.groupby("method")[["in_tok", "out_tok"]].sum().sum(1)
    pick = {}
    for k, g in dv.groupby(keys):
        acc = g.groupby("method").correct.mean()
        best = acc[acc == acc.max()].index
        pick[k] = min(best, key=lambda m: cost.get(m, 0))
    default = dv.groupby("method").correct.mean().idxmax()
    ts = test[test.method.isin(cands)].copy()
    ts["route"] = [pick.get(tuple(r[k] for k in keys), default) for _, r in ts.iterrows()]
    routed = ts[ts.method == ts.route]
    res = {m: test[test.method == m].correct.mean() for m in cands}
    res["router"] = routed.correct.mean()
    res["oracle_best_per_item"] = ts.groupby("item_id").correct.max().mean()
    return pd.Series(res).round(3), pd.Series(pick).rename("chosen")

def fig_margin(df, out):
    df = df[df.method.isin(COLORS)].copy()
    df["bin"] = pd.cut(df["margin_steps"].abs(), [-0.01, 0.5, 1, 2, 5, np.inf], labels=["≤0.5", "0.5–1", "1–2", "2–5", ">5"])
    t = df.pivot_table(index="bin", columns="method", values="correct", aggfunc="mean", observed=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.6), facecolor="#fcfcfb")
    for m in [c for c in COLORS if c in t]:
        ax.plot(range(len(t)), t[m], marker="o", ms=5, lw=2, color=COLORS[m], label=m)
    ax.set_xticks(range(len(t))); ax.set_xticklabels(t.index)
    ax.set_xlabel("Distance from threshold (ladder steps)"); ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.02); ax.grid(axis="y", color="#e6e5e0", lw=0.8); ax.set_facecolor("#fcfcfb")
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)

def fig_gain(g, col, out):
    if g.empty:
        return
    fig, ax = plt.subplots(figsize=(6.4, 0.5 + 0.45 * len(g)), facecolor="#fcfcfb")
    y = np.arange(len(g))
    colors = ["#2a78d6" if v >= 0 else "#e34948" for v in g.gain]
    ax.errorbar(g.gain, y, xerr=[g.gain - g.ci_low, g.ci_high - g.gain], fmt="none", ecolor="#8a8984", lw=1.2, capsize=3)
    ax.scatter(g.gain, y, c=colors, s=40, zorder=3)
    ax.axvline(0, color="#52514e", lw=1)
    ax.set_yticks(y); ax.set_yticklabels([f"{k} (n={n})" for k, n in zip(g[col], g.n)])
    ax.set_xlabel("Accuracy gain of C4 over C2 (95% CI)"); ax.set_facecolor("#fcfcfb")
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)

def md(df):
    return df.to_markdown() if len(df) else "_(no data)_"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--evidence", default="report")
    a = ap.parse_args()
    out = ROOT / "results" / slug(a.model) / a.evidence
    out.mkdir(parents=True, exist_ok=True)
    full = with_features(load(a.model, a.evidence))
    parts = ["# Results: " + a.model + " / evidence=" + a.evidence]
    for split in ["dev", "test"]:
        df = full[full.split == split]
        if df.empty:
            continue
        s = summary(df).reindex([m for m in ORDER if m in set(df.method)])
        parts += [f"\n## {split}: overall\n", md(s)]
        if {"C2_cot", "C4_spec_code"} <= set(df.method):
            df = df.assign(cell=df.strike_type + " / " + np.where(df.near, "near", "far"))
            for col in ["domain", "cell", "distractor_flip"] + (["prior_conflict"] if "prior_conflict" in df else []):
                g = gain_by(df, "C4_spec_code", "C2_cot", col)
                parts += [f"\n### {split}: C4 vs C2 by {col}\n", md(g)]
                if col == "cell":
                    fig_gain(g, col, out / f"gain_cell_{split}.png")
            parts += [f"\n### {split}: when-regression (C4 vs C2, cluster-robust by event)\n", md(regression(df))]
        parts += [f"\n### {split}: structured pipeline stage accuracy\n", md(stage_table(df))]
        parts += [f"\n### {split}: where structured errors come from (counts)\n", md(error_budget(df))]
        fig_margin(df, out / f"accuracy_vs_margin_{split}.png")
    dev, test = full[full.split == "dev"], full[full.split == "test"]
    if not dev.empty and not test.empty and {"C2_cot", "C4_spec_code"} <= set(dev.method) & set(test.method):
        res, pick = router(dev, test)
        parts += ["\n## Router (rules learned on dev, scored on test)\n", md(res.to_frame("test_acc")), "\n", md(pick.to_frame())]
    (out / "summary.md").write_text("\n".join(parts) + "\n")
    print(f"wrote {out.relative_to(ROOT)}/summary.md and figures")

if __name__ == "__main__":
    main()
