"""Cross-model tables for the Milestone 3 report (dev split). Writes results/m3/tables.md.
Every number in the report must come from this file's output."""
import json, warnings
import numpy as np
import pandas as pd
from config import ROOT, PROC, RAW
from evaluate import load, bal_acc, paired_diff, tolerant_view
from evidence import cli_numbers
from methods import evaluate_spec, normalize_spec, gold_spec

warnings.filterwarnings("ignore")
MODELS = [("allam-2-7b", "ALLaM 7B"), ("qwen/qwen3.8-27b", "Qwen 27B"), ("openai/gpt-oss-20b", "gpt-oss 20B")]
EVID = ["report", "report_both"]
ORDER = ["B1_no_evidence", "C1_direct", "C2_cot", "C3_spec_prose", "C4_spec_code", "O1_C4_gold_spec", "O2_C4_gold_value"]
PAIRS = [("C2_cot", "C1_direct"), ("C4_spec_code", "C1_direct"), ("C4_spec_code", "C2_cot"),
         ("C3_spec_prose", "C4_spec_code"), ("O1_C4_gold_spec", "C4_spec_code"), ("O2_C4_gold_value", "C4_spec_code")]
PIL = {"KXHIGHNY": "CLINYC", "KXLOWTNYC": "CLINYC", "KXHIGHCHI": "CLIMDW", "KXHIGHMIA": "CLIMIA",
       "KXHIGHAUS": "CLIAUS", "KXHIGHLAX": "CLILAX", "KXHIGHDEN": "CLIDEN", "KXHIGHPHIL": "CLIPHL"}

ITEMS = pd.read_pickle(PROC / "items_study_feat.pkl").set_index("item_id")

def prelim_value(item):
    pil = PIL.get(item["series"])
    if not pil:
        return None
    d = json.load(open(RAW / "cli" / f"{pil}.json")).get(str(item["obs_date"])[:10], {})
    v = (d.get("prelim") or {}).get("max" if item["measure"] == "maximum" else "min")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def value_source(item_id, pred):
    """Name the report number that a wrong extracted value matches (record, normal, ...)."""
    if pred is None or pd.isna(pred):
        return "no value"
    it = ITEMS.loc[item_id].to_dict(); it["item_id"] = item_id
    if it["domain"] != "weather":
        return "other"
    nums = cli_numbers(it)
    want = "maximum" if it["measure"] == "maximum" else "minimum"
    other = "minimum" if want == "maximum" else "maximum"
    for k, v in (nums.get(want) or {}).items():
        if k != "observed" and v is not None and abs(float(v) - float(pred)) < 1e-6:
            return k
    if (nums.get(other) or {}).get("observed") is not None and abs(float(nums[other]["observed"]) - float(pred)) < 1e-6:
        return "other extreme"
    pv = prelim_value(it)
    if pv is not None and abs(pv - float(pred)) < 1e-6:
        return "preliminary report"
    return "other"

def overall(df):
    rows = []
    for m in [x for x in ORDER if x in set(df.method)]:
        g = df[df.method == m]
        t = tolerant_view(g)
        rows.append({"method": m, "n": len(g), "acc": g.correct.mean(), "acc_tol": t.correct.mean(),
                     "bal_acc": bal_acc(g), "bal_acc_tol": bal_acc(t),
                     "no_answer": g.verdict.isin(["ABSTAIN", "INVALID"]).mean(),
                     "no_answer_tol": t.verdict.isin(["ABSTAIN", "INVALID"]).mean(),
                     "calls": g.calls.mean(), "tokens": (g.in_tok + g.out_tok).mean()})
    return pd.DataFrame(rows).round(3)

def pairs(df):
    rows = []
    for a, b in PAIRS:
        if {a, b} <= set(df.method):
            for mode, dd in (("strict", df), ("tolerant", tolerant_view(df))):
                d, lo, hi, n = paired_diff(dd, a, b)
                rows.append({"compare": f"{a} - {b}", "scoring": mode, "n": n, "diff": d, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows).round(3)

def slices(df):
    """Tolerant scoring, so a format slip does not hide where the reasoning fails."""
    d = tolerant_view(df).join(ITEMS[["near", "distractor_flip"]], on="item_id")
    d["shape"] = np.where(d.strike_type == "between", "between (2 bounds)", "one-sided")
    out = []
    for col in ["domain", "near", "distractor_flip", "shape"]:
        t = d[d.method.isin(["C1_direct", "C2_cot", "C3_spec_prose", "C4_spec_code"])]
        p = t.pivot_table(index=col, columns="method", values="correct", aggfunc="mean").round(3)
        p.insert(0, "n_items", t.groupby(col).item_id.nunique())
        out.append((col, p))
    return out

def c4_errors(df):
    """Why strict C4 is wrong. First cause in this order: the extractor JSON was cut off (value recovered
    from the cached text), a spec format slip (normalize_spec fixes it), then, for items still wrong under
    tolerant scoring, the spec meaning or the extracted value."""
    s = df[(df.method == "C4_spec_code") & ~df.correct.astype(bool)].copy()
    if s.empty:
        return pd.DataFrame(), pd.DataFrame()
    gv = s.value.astype(float)
    raw_spec_ok = [evaluate_spec(sp, v) == g for sp, v, g in zip(s.spec, gv, s.gold)]
    norm_spec_ok = [evaluate_spec(normalize_spec(sp), v) == g for sp, v, g in zip(s.spec, gv, s.gold)]
    cut = s.pred_value.isna() & s.pred_value_tol.notna()
    val_ok = [pd.notna(pv) and abs(pv - v) < 1e-6 for pv, v in zip(s.pred_value_tol, gv)]
    cause = []
    for c, r, n, vo, tol in zip(cut, raw_spec_ok, norm_spec_ok, val_ok, s.correct_tol):
        if tol:
            cause.append("format: extractor JSON cut off" if c else "format: spec field slip")
        elif not n and not vo:
            cause.append("still wrong: spec meaning + value")
        elif not n:
            cause.append("still wrong: spec meaning")
        else:
            cause.append("still wrong: value")
    s["cause"] = cause
    s["value_from"] = [value_source(i, pv) if not vo else "" for i, pv, vo in zip(s.item_id, s.pred_value_tol, val_ok)]
    still = s[s.cause.str.startswith("still") & s.cause.str.contains("value")]
    return s.groupby(["domain", "cause"]).size().unstack(fill_value=0), \
        still.groupby("value_from").size().rename("n").to_frame()

def md(df):
    return df.to_markdown() if len(df) else "_(no data)_"

def main():
    parts = ["# Milestone 3 tables (dev split, generated by src/m3_report.py)\n"]
    summary = {}
    for model, name in MODELS:
        for ev in EVID:
            try:
                df = load(model, ev)
            except Exception:
                continue
            if df.empty:
                continue
            df = df[df.split == "dev"]
            if df.empty:
                continue
            parts += [f"\n## {name} | evidence: {ev}\n", "\n### overall\n", md(overall(df)),
                      "\n\n### paired differences (95% CI, bootstrap by event)\n", md(pairs(df))]
            for col, p in slices(df):
                parts += [f"\n\n### accuracy by {col}\n", md(p)]
            key = f"{name} | {ev}"
            summary[key] = {"overall": overall(df).set_index("method").to_dict("index"),
                            "pairs": pairs(df).to_dict("records"),
                            "slices": {col: p.reset_index().to_dict("records") for col, p in slices(df)}}
            e, v = c4_errors(df)
            summary[key]["c4_causes"] = e.reset_index().to_dict("records") if len(e) else []
            summary[key]["c4_value_from"] = v.reset_index().to_dict("records") if len(v) else []
            parts += ["\n\n### C4 error causes\n", md(e), "\n\n### where a wrong C4 value came from\n", md(v)]
    out = ROOT / "results" / "m3"; out.mkdir(parents=True, exist_ok=True)
    (out / "tables.md").write_text("\n".join(parts) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=lambda x: None if pd.isna(x) else str(x)))
    print("\n".join(parts))

if __name__ == "__main__":
    main()
