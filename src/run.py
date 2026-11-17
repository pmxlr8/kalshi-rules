import argparse, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from config import PROC, RUNS
from evidence import bundle
from methods import METHODS, gold_spec
from llm import LLM

class FakeLLM:
    model = "fake"
    def __init__(self):
        self.item = None
    def chat(self, messages, **kw):
        u = messages[-1]["content"]
        if u.startswith("Read only the contract rules"):
            t = json.dumps(gold_spec(self.item))
        elif u.startswith("From the evidence"):
            t = json.dumps({"value": self.item["value"], "quote": "fake"})
        else:
            t = '{"verdict": "NO", "confidence": 0.5}'
        return {"text": t, "in_tok": len(u) // 4, "out_tok": 20, "latency": 0.0, "cached": False}

def out_path(model, evidence, method):
    p = RUNS / re.sub(r"[^A-Za-z0-9_.-]", "_", model) / evidence / f"{method}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def done_ids(path):
    return {json.loads(l)["item_id"] for l in path.open()} if path.exists() else set()

def run_one(llm, method, it, evidence):
    ev = bundle(it, evidence) or bundle(it, "clean")
    if isinstance(llm, FakeLLM):
        llm.item = it
    res = METHODS[method](llm, it, ev)
    gold = it["result"].upper()
    keep = ["item_id", "domain", "series", "event", "split", "strike_type", "margin", "margin_steps", "value"]
    rec = {k: (None if pd.isna(it[k]) else it[k]) for k in keep}
    rec.update({"method": method, "evidence": evidence if bundle(it, evidence) else "clean", "gold": gold,
                "correct": res["verdict"] == gold, **{k: v for k, v in res.items() if k != "value"},
                "pred_value": res.get("value")})
    rec["raw"] = (rec.get("raw") or "")[:2000]
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama-3.1-8b-instant")
    ap.add_argument("--methods", default="C1_direct,C2_cot,C4_spec_code")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--domains", default="weather,fin,econ")
    ap.add_argument("--evidence", default="report")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fake", action="store_true")
    a = ap.parse_args()

    items = pd.read_pickle(PROC / "items_study.pkl")
    items = items[(items.split == a.split) & items.domain.isin(a.domains.split(","))]
    if a.limit:
        items = items.sample(min(a.limit, len(items)), random_state=0)
    llm = FakeLLM() if a.fake else LLM(a.model)
    workers = 1 if a.fake else a.workers
    for method in a.methods.split(","):
        path = out_path(llm.model, a.evidence, method)
        todo = [r for _, r in items.iterrows() if r["item_id"] not in done_ids(path)]
        n_ok = n = 0
        with ThreadPoolExecutor(workers) as ex, path.open("a") as f:
            futs = [ex.submit(run_one, llm, method, it.to_dict(), a.evidence) for it in todo]
            for fu in as_completed(futs):
                rec = fu.result()
                f.write(json.dumps(rec, default=str) + "\n")
                n += 1; n_ok += rec["correct"]
        print(f"{method}: {n} new items, accuracy on new {n_ok / max(n, 1):.3f} -> {path.relative_to(RUNS)}")

if __name__ == "__main__":
    main()
