import json, re
from collections import Counter

SYSTEM = ("You resolve prediction market contracts. Apply the contract's written rules to the evidence. "
          "Answer YES if the rules' YES condition is met, NO if it is not met, and ABSTAIN only if the evidence cannot decide.")
VERDICT_JSON = 'Return only JSON: {"verdict": "YES" | "NO" | "ABSTAIN", "confidence": <number from 0 to 1>}'
COMPARATORS = {"greater": ">", "greater_or_equal": ">=", "less": "<", "less_or_equal": "<=", "between": "between"}

def contract(it, rules=True):
    s = f"Market title: {it['title']}\n"
    if rules:
        s += f"YES outcome label: {it['yes_sub_title']}\nRules:\n{it['rules_primary']}\n{it['rules_secondary']}".rstrip()
    return s

def last_json(text):
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text or "", re.S))):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None

def verdict_of(d):
    v = str((d or {}).get("verdict", "")).upper().strip()
    return v if v in {"YES", "NO", "ABSTAIN"} else "INVALID"

def conf_of(d):
    try:
        return float((d or {}).get("confidence"))
    except (TypeError, ValueError):
        return None

def ask(llm, user, max_tokens, temperature=0.0, sample=0):
    r = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                 temperature=temperature, max_tokens=max_tokens, sample=sample)
    return r, last_json(r["text"])

def usage(*rs):
    return {"calls": len(rs), "in_tok": sum(r["in_tok"] for r in rs), "out_tok": sum(r["out_tok"] for r in rs),
            "latency": round(sum(r["latency"] for r in rs), 3)}

def direct(llm, it, ev, rules=True, evidence=True):
    body = contract(it, rules)
    if evidence:
        r, d = ask(llm, f"{body}\n\nEvidence:\n{ev}\n\n{VERDICT_JSON}", 60)
    else:
        r, d = ask(llm, f"{body}\n\nNo evidence is available. You must still answer YES or NO with your best guess "
                        f"of how this market settled; do not abstain.\n\n{VERDICT_JSON}", 60)
    return {"verdict": verdict_of(d), "confidence": conf_of(d), "raw": r["text"], **usage(r)}

def cot(llm, it, ev, temperature=0.0, sample=0, extra=""):
    user = (f"{contract(it)}{extra}\n\nEvidence:\n{ev}\n\nReason step by step in at most 150 words. "
            f"Then, on the last line, {VERDICT_JSON[0].lower() + VERDICT_JSON[1:]}")
    r, d = ask(llm, user, 400, temperature, sample)
    return {"verdict": verdict_of(d), "confidence": conf_of(d), "raw": r["text"], **usage(r)}

def cot_sc(llm, it, ev, k=5):
    outs = [cot(llm, it, ev, temperature=0.7, sample=i + 1) for i in range(k)]
    votes = Counter(o["verdict"] for o in outs if o["verdict"] != "INVALID")
    top = votes.most_common()
    verdict = top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) else "ABSTAIN"
    agree = top[0][1] / k if top else 0.0
    return {"verdict": verdict, "confidence": agree, "raw": json.dumps([o["verdict"] for o in outs]),
            "calls": k, "in_tok": sum(o["in_tok"] for o in outs), "out_tok": sum(o["out_tok"] for o in outs),
            "latency": round(sum(o["latency"] for o in outs), 3)}

SPEC_PROMPT = """Read only the contract rules below and turn the YES condition into a JSON spec.
Fields:
- "quantity": what must be measured, in plain words (include place and date)
- "unit": unit of the quantity
- "comparator": one of ">", ">=", "<", "<=", "between" ("between" includes both ends)
- "threshold": the number to compare against, for ">", ">=", "<" and "<=" (null for "between")
- "low", "high": the two ends, only for "between" (null otherwise)
Return only the JSON object.

{contract}"""

FACT_PROMPT = """From the evidence, extract the measured value of this quantity: {quantity} (unit: {unit}).
Copy the line you used, word for word, as "quote". If the evidence does not state it, use null.
Return only JSON: {{"value": <number or null>, "quote": "<text>"}}

Evidence:
{evidence}"""

APPLY_PROMPT = """Contract YES condition (as a spec): {spec}
Measured value: {value} (source line: "{quote}")
Decide the contract. Reason in at most 80 words, then, on the last line, {vj}"""

def write_spec(llm, it):
    r, d = ask(llm, SPEC_PROMPT.format(contract=contract(it)), 200)
    return r, d

def gold_spec(it):
    c = COMPARATORS.get(it["strike_type"])
    t = it["floor"] if c in (">", ">=") else it["cap"] if c in ("<", "<=") else None
    lo, hi = (it["floor"], it["cap"]) if c == "between" else (None, None)
    if it["domain"] == "weather":
        q, u = f"the {it['measure']} temperature at {it['station']} on {it['obs_date']}", "degrees F"
    else:
        q, u = it["title"], ""
    return {"quantity": q, "unit": u, "comparator": c, "threshold": t, "low": lo, "high": hi}

def extract_fact(llm, spec, ev):
    q = (spec or {}).get("quantity") or "the quantity named in the contract"
    r, d = ask(llm, FACT_PROMPT.format(quantity=q, unit=(spec or {}).get("unit", ""), evidence=ev), 150)
    return r, d

def to_num(x):
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", "").replace("°", ""))
    except (TypeError, ValueError):
        return None

def evaluate_spec(spec, value):
    if not spec or value is None:
        return "ABSTAIN"
    c = spec.get("comparator")
    t, lo, hi = to_num(spec.get("threshold")), to_num(spec.get("low")), to_num(spec.get("high"))
    try:
        if c == ">": ok = value > t
        elif c == ">=": ok = value >= t
        elif c == "<": ok = value < t
        elif c == "<=": ok = value <= t
        elif c == "between": ok = lo <= value <= hi
        else: return "ABSTAIN"
    except TypeError:
        return "ABSTAIN"
    return "YES" if ok else "NO"

CMP_WORDS = [("greater than or equal", ">="), ("at least", ">="), ("≥", ">="), ("=>", ">="), (">=", ">="),
             ("less than or equal", "<="), ("at most", "<="), ("≤", "<="), ("=<", "<="), ("<=", "<="),
             ("greater", ">"), ("above", ">"), ("more than", ">"), ("exceed", ">"), (">", ">"),
             ("less", "<"), ("below", "<"), ("under", "<"), ("<", "<"), ("between", "between"), ("range", "between")]

def num_loose(x):
    """First number in x (handles '68°F', '$4.35', '-0.2%'). None if there is none."""
    v = to_num(x)
    if v is not None:
        return v
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace(",", "")) if x is not None else None
    return float(m.group(0)) if m else None

def normalize_spec(spec):
    """Format-tolerant reading of an LLM spec, used post hoc (C4N). It only repairs the format:
    comparator words, a [low, high] pair put in "threshold", a one-sided bound put in low or high."""
    if not isinstance(spec, dict):
        return spec
    s = dict(spec)
    c = str(s.get("comparator") or "").strip().lower()
    s["comparator"] = next((sym for w, sym in CMP_WORDS if w in c), c)
    t = s.get("threshold")
    if s["comparator"] == "between":
        lo, hi = num_loose(s.get("low")), num_loose(s.get("high"))
        if (lo is None or hi is None) and t is not None:
            parts = t if isinstance(t, (list, tuple)) else re.findall(r"-?\d+(?:\.\d+)?", str(t).replace(",", ""))
            if len(parts) == 2:
                lo, hi = num_loose(parts[0]), num_loose(parts[1])
        if lo is not None and hi is not None and lo > hi:
            lo, hi = hi, lo
        s["low"], s["high"] = lo, hi
    else:
        v = num_loose(t)
        if v is None:
            ends = [num_loose(s.get(k)) for k in ("low", "high") if num_loose(s.get(k)) is not None]
            v = ends[0] if len(ends) == 1 else None
        s["threshold"] = v
    return s

def structured(llm, it, ev, apply="code", spec_override=None, value_override=None):
    rs = []
    if spec_override is None:
        r, spec = write_spec(llm, it); rs.append(r)
    else:
        spec = spec_override
    if value_override is None:
        r, fact = extract_fact(llm, spec, ev); rs.append(r)
        value, quote = to_num((fact or {}).get("value")), (fact or {}).get("quote", "")
    else:
        value, quote = value_override, "(gold value)"
    if apply == "code":
        verdict, conf = evaluate_spec(spec, value), None
    else:
        r, d = ask(llm, APPLY_PROMPT.format(spec=json.dumps(spec), value=value, quote=quote,
                                            vj=VERDICT_JSON[0].lower() + VERDICT_JSON[1:]), 300)
        rs.append(r)
        verdict, conf = verdict_of(d), conf_of(d)
    u = usage(*rs) if rs else {"calls": 0, "in_tok": 0, "out_tok": 0, "latency": 0}
    return {"verdict": verdict, "confidence": conf, "spec": spec, "value": value, "quote": quote,
            "raw": json.dumps({"spec": spec, "value": value}), **u}

METHODS = {
    "B1_no_evidence": lambda llm, it, ev: direct(llm, it, ev, evidence=False),
    "B2_no_rules": lambda llm, it, ev: direct(llm, it, ev, rules=False),
    "C1_direct": lambda llm, it, ev: direct(llm, it, ev),
    "C2_cot": lambda llm, it, ev: cot(llm, it, ev),
    "C2SC_cot_vote5": lambda llm, it, ev: cot_sc(llm, it, ev, k=5),
    "C3_spec_prose": lambda llm, it, ev: structured(llm, it, ev, apply="llm"),
    "C4_spec_code": lambda llm, it, ev: structured(llm, it, ev, apply="code"),
    "O1_C4_gold_spec": lambda llm, it, ev: structured(llm, it, ev, spec_override=gold_spec(it)),
    "O2_C4_gold_value": lambda llm, it, ev: structured(llm, it, ev, value_override=it["value"]),
    "O3_C2_gold_spec_text": lambda llm, it, ev: cot(llm, it, ev, extra="\n\nThe YES condition as a spec: " + json.dumps(gold_spec(it))),
}
