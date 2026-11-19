import numpy as np
import pandas as pd
from config import PROC
from evidence import cli_numbers
from methods import evaluate_spec, gold_spec

def add_features(items):
    df = items.copy()
    df["near"] = df["margin_steps"].abs() <= 1
    dep, flip, kinds = [], [], []
    for _, r in df.iterrows():
        if r["domain"] != "weather":
            dep.append(np.nan); flip.append(False); kinds.append("")
            continue
        nums = cli_numbers(r)
        own = nums.get(r["measure"], {})
        other = nums.get("minimum" if r["measure"] == "maximum" else "maximum", {})
        dep.append(own.get("departure"))
        spec, gold = gold_spec(r), r["result"].upper()
        cands = {"normal": own.get("normal"), "record": own.get("record"), "last_year": own.get("last_year"),
                 "other_measure": other.get("observed")}
        flips = [k for k, v in cands.items() if v is not None and evaluate_spec(spec, v) != gold]
        flip.append(bool(flips)); kinds.append(",".join(flips))
    df["departure"] = dep
    df["abs_departure"] = df["departure"].abs()
    df["distractor_flip"] = flip
    df["flipping_distractors"] = kinds
    return df

if __name__ == "__main__":
    f = add_features(pd.read_parquet(PROC / "items_study.parquet"))
    f.to_parquet(PROC / "items_study_feat.parquet", index=False, compression="zstd")
    w = f[f.domain == "weather"]
    print(f"weather items: {len(w)}  near threshold: {w.near.mean():.2f}  a distractor value would flip the answer: {w.distractor_flip.mean():.2f}")
    print("which distractors flip:", w.flipping_distractors.str.split(",").explode().replace("", np.nan).dropna().value_counts().to_dict())
    print("|departure from normal| quartiles:", w.abs_departure.quantile([.25, .5, .75]).round(1).to_dict())
