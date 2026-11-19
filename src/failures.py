import argparse
import pandas as pd
from config import ROOT, PROC, DEFAULT_MODEL, slug
from evaluate import load

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--evidence", default="report")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--per_method", type=int, default=30)
    a = ap.parse_args()
    df = load(a.model, a.evidence)
    feat = pd.read_parquet(PROC / "items_study_feat.parquet")[["item_id", "title", "rules_primary", "near", "distractor_flip", "flipping_distractors"]]
    wrong = df[(df.split == a.split) & ~df.correct.astype(bool)].merge(feat, on="item_id", how="left")
    wrong = wrong.groupby("method", group_keys=False).apply(lambda g: g.sample(min(a.per_method, len(g)), random_state=0), include_groups=True)
    cols = ["method", "item_id", "domain", "strike_type", "near", "distractor_flip", "flipping_distractors", "value", "gold",
            "verdict", "pred_value", "quote", "spec", "title", "rules_primary", "raw"]
    out = ROOT / "results" / slug(a.model) / a.evidence / f"failures_{a.split}.csv"
    wrong.reindex(columns=cols).assign(error_type="", cause="", notes="").to_csv(out, index=False)
    print(f"wrote {len(wrong)} wrong cases to {out.relative_to(ROOT)} (fill error_type, cause, notes by hand)")

if __name__ == "__main__":
    main()
