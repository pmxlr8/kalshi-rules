"""Item-by-item audit of strict C4 errors (ALLaM 7B, one report): which repair, if any, tolerant scoring used.
Writes results/m3/c4_repairs.csv. Every count in the report about C4 repairs comes from this file."""
import re
import pandas as pd
from config import ROOT
from evaluate import load
from methods import evaluate_spec, normalize_spec, CMP_WORDS

def spec_repair(sp):
    """Name the normalize_spec rule that changes this spec, or "" if none does."""
    if not isinstance(sp, dict):
        return "no spec"
    n = normalize_spec(sp); kinds = []
    c = str(sp.get("comparator") or "").strip().lower()
    if n["comparator"] != c:
        kinds.append("comparator word")
    if n["comparator"] == "between":
        lo, hi = sp.get("low"), sp.get("high")
        if (lo is None or hi is None) and sp.get("threshold") is not None and n["low"] is not None:
            kinds.append("between bounds in threshold " + ("list" if isinstance(sp["threshold"], (list, tuple)) else "string"))
        elif n["low"] != lo or n["high"] != hi:
            kinds.append("bounds as text or swapped")
    else:
        t = sp.get("threshold")
        if n["threshold"] != t:
            kinds.append("one-sided bound in low/high" if t is None else "threshold as text")
    return "; ".join(kinds)

def main():
    df = load("allam-2-7b", "report")
    df = df[df.split == "dev"]
    s = df[(df.method == "C4_spec_code") & ~df.correct.astype(bool)].copy()
    v = s.value.astype(float)
    s["json_cut"] = s.pred_value.isna() & s.pred_value_tol.notna()
    s["no_value_at_all"] = s.pred_value_tol.isna()
    s["recovered_value_right"] = [bool(c) and abs(pv - g) < 1e-6 for c, pv, g in zip(s.json_cut, s.pred_value_tol, v)]
    s["spec_repair"] = [spec_repair(sp) for sp in s.spec]
    s["raw_spec_right"] = [evaluate_spec(sp, g) == y for sp, g, y in zip(s.spec, v, s.gold)]
    s["norm_spec_right"] = [evaluate_spec(normalize_spec(sp), g) == y for sp, g, y in zip(s.spec, v, s.gold)]
    cols = ["item_id", "domain", "gold", "value", "pred_value", "pred_value_tol", "json_cut", "recovered_value_right",
            "no_value_at_all", "spec_repair", "raw_spec_right", "norm_spec_right", "correct_tol", "spec"]
    out = s[cols].sort_values("item_id")
    out.to_csv(ROOT / "results" / "m3" / "c4_repairs.csv", index=False)
    print("strict C4 errors:", len(out))
    print("JSON cut, value recovered:", int(out.json_cut.sum()), " of these right:", int(out.recovered_value_right.sum()))
    print("no value even after recovery:", int(out.no_value_at_all.sum()))
    print(out.spec_repair.replace("", "(none)").value_counts().to_string())
    print(pd.crosstab([out.json_cut, out.spec_repair != ""], out.correct_tol).to_string())

if __name__ == "__main__":
    main()
