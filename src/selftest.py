import pandas as pd
from config import PROC
from methods import evaluate_spec, gold_spec, last_json, verdict_of

def main():
    items = pd.read_pickle(PROC / "items_study.pkl")
    agree = [evaluate_spec(gold_spec(r), r["value"]) == r["result"].upper() for _, r in items.iterrows()]
    assert all(agree), f"gold spec disagrees on {len(agree) - sum(agree)} items"
    assert evaluate_spec({"comparator": ">", "threshold": 56}, 56.0) == "NO"
    assert evaluate_spec({"comparator": ">=", "threshold": 56}, 56.0) == "YES"
    assert evaluate_spec({"comparator": "<", "threshold": 49}, 49.0) == "NO"
    assert evaluate_spec({"comparator": "between", "low": 49, "high": 50}, 49.0) == "YES"
    assert evaluate_spec({"comparator": ">", "low": 1}, None) == "ABSTAIN"
    assert verdict_of(last_json('think... {"a": 1}\n{"verdict": "yes", "confidence": 0.9}')) == "YES"
    assert verdict_of(last_json("no json here")) == "INVALID"
    print(f"selftest passed: gold spec reproduces all {len(items)} study outcomes; evaluator and parser checks ok")

if __name__ == "__main__":
    main()
