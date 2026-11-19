"""Data and pilot numbers for the Milestone 3 report. Writes results/m3/numbers.json.
Run m3_report.py first (it writes results/m3/summary.json, the model results)."""
import json, math, re
import pandas as pd
from evaluate import load
from config import ROOT, PROC, RUNS
from evidence import weather_report
from methods import evaluate_spec, normalize_spec, gold_spec
from m3_report import prelim_value

def data_numbers():
    a = pd.read_pickle(PROC / "items_all.pkl")
    s = pd.read_pickle(PROC / "items_study_feat.pkl")
    num = a[a.value.notna()]
    agree = sum(evaluate_spec(gold_spec(r), r["value"]) == r["result"].upper() for _, r in num.iterrows())
    w = a[a.domain == "weather"].drop_duplicates(["station", "obs_date", "measure"])
    miss = bad = 0
    for _, r in w.iterrows():
        _, prod = weather_report(r)
        if prod is None:
            miss += 1
            continue
        got = prod["max"] if r["measure"] == "maximum" else prod["min"]
        try:
            bad += float(got) != float(r["value"])
        except (TypeError, ValueError):
            bad += 1
    rev = {}
    for split in ["dev", "test"]:
        ws = s[(s.domain == "weather") & (s.split == split)]
        differs = flips = 0
        for _, r in ws.iterrows():
            pv = prelim_value(r.to_dict())
            if pv is not None and pv != float(r["value"]):
                differs += 1
                flips += evaluate_spec(gold_spec(r), pv) != r["result"].upper()
        rev[split] = {"n": len(ws), "differs": differs, "flips": flips}
    return {
        "markets": len(a), "series": int(a.series.nunique()), "numeric_value": len(num),
        "text_label_only": int(a.value.isna().sum()), "gold_agree_numeric": int(agree),
        "first_close": a.close_time.min()[:10], "last_close": a.close_time.max()[:10],
        "station_days": len(w), "missing_reports": miss, "value_mismatch": int(bad),
        "study": len(s), "events": int(s.event.nunique()),
        "by_domain": s.domain.value_counts().to_dict(),
        "by_split": s.split.value_counts().to_dict(), "events_by_split": s.groupby("split").event.nunique().to_dict(),
        "yes_rate": s.groupby("domain").result.apply(lambda x: round((x.str.upper() == "YES").mean(), 3)).to_dict(),
        "dev_near": int(s[s.split == "dev"].near.sum()), "dev_dflip": int(s[s.split == "dev"].distractor_flip.sum()),
        "test_dflip": int(s[s.split == "test"].distractor_flip.sum()),
        "weather_dflip_share": round(float(s[s.domain == "weather"].distractor_flip.mean()), 3),
        "revisions": rev,
    }

def pilot_numbers():
    out = {}
    for p in sorted((RUNS / "pilot_v1").glob("*.jsonl")):
        r = [json.loads(l) for l in p.open()]
        out[p.stem] = {"n": len(r), "correct": sum(x["correct"] for x in r),
                       "abstain": sum(x["verdict"] == "ABSTAIN" for x in r)}
    c4 = [json.loads(l) for l in (RUNS / "pilot_v1" / "C4_spec_code.jsonl").open()]
    out["C4_v1_tolerant"] = sum(evaluate_spec(normalize_spec(x["spec"]), x["pred_value"]) == x["gold"] for x in c4)
    ids = {x["item_id"] for x in c4}
    v2 = [json.loads(l) for l in (RUNS / "qwen_qwen3.8-27b" / "report" / "C4_spec_code.jsonl").open()]
    v2 = [x for x in v2 if x["item_id"] in ids]
    out["C4_v2_same_items"] = {"n": len(v2), "correct": sum(x["correct"] for x in v2)}
    return out

def error_numbers():
    """Direct-answer (C1) error patterns, and C1 errors that C4 fixes (tolerant scoring, dev)."""
    out = {}
    for model, name in [("allam-2-7b", "ALLaM 7B"), ("qwen/qwen3.8-27b", "Qwen 27B"), ("openai/gpt-oss-20b", "gpt-oss 20B")]:
        for ev in ["report", "report_both"]:
            df = load(model, ev)
            if df.empty:
                continue
            df = df[df.split == "dev"]
            c1 = df[df.method == "C1_direct"]
            if c1.empty:
                continue
            c4 = df[df.method == "C4_spec_code"].set_index("item_id").correct_tol
            o = {"c1_n": len(c1), "c1_invalid_strict": int((c1.verdict == "INVALID").sum()),
                 "c1_abstain": int((c1.verdict_tol == "ABSTAIN").sum()),
                 "c1_yes_rate": round(float((c1.verdict_tol == "YES").mean()), 3),
                 "gold_yes_rate": round(float((c1.gold == "YES").mean()), 3)}
            for dom in ["weather", "all"]:
                w = c1[~c1.correct_tol & ((c1.domain == dom) | (dom == "all"))]
                kinds = {"no value stated": 0, "wrong value": 0, "right value, wrong comparison": 0}
                for _, r in w.iterrows():
                    nums = [float(x) for x in re.findall(r"(-?\d+(?:\.\d+)?)\s*°", r.raw or "")]
                    k = "no value stated" if not nums else "right value, wrong comparison" if abs(nums[0] - r.value) < 1e-6 else "wrong value"
                    kinds[k] += 1
                both = [i for i in w.item_id if i in c4.index]
                o[dom] = {"c1_errors": len(w), "yes_on_no": int(((w.verdict_tol == "YES") & (w.gold == "NO")).sum()),
                          "kinds": kinds if dom == "weather" else None,
                          "c4_has": len(both), "c4_fixes": int(c4.loc[both].sum()) if both else 0}
            out[f"{name} | {ev}"] = o
    return out

def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, float) and math.isnan(x):
        return None
    return x

def main():
    out = ROOT / "results" / "m3"
    summary = json.loads((out / "summary.json").read_text().replace("NaN", "null"))
    nums = clean({"data": data_numbers(), "pilot": pilot_numbers(), "errors": error_numbers(), "results": summary})
    (out / "numbers.json").write_text(json.dumps(nums, indent=1, default=str, allow_nan=False))
    print(json.dumps({k: nums[k] for k in ("data", "pilot", "errors")}, indent=1, default=str))

if __name__ == "__main__":
    main()
