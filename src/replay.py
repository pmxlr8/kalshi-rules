"""Replay a finished run from the cache (no API calls) to recover the raw text of each step.
Used by tolerant scoring: when the extractor's JSON is cut off (for example by a long verbatim quote),
the value it already wrote can still be read."""
import re
import pandas as pd
from config import PROC
from evidence import bundle
from llm import LLM
from methods import METHODS

VALUE_RE = re.compile(r'"value"\s*:\s*"?(-?\d+(?:\.\d+)?)')

class CacheOnly(LLM):
    """Same cache keys as LLM, but a cache miss raises instead of calling the API."""
    def __init__(self, model):
        super().__init__(model)
        self.client, self.log = None, []

    def chat(self, messages, **kw):
        r = super().chat(messages, **kw)  # a miss fails on client=None
        self.log.append((messages[-1]["content"], r["text"]))
        return r

_LLMS, _ITEMS = {}, None

def fact_text(model, item_id, method, evidence):
    """Raw text of the fact-extraction call for one finished item, or None."""
    global _ITEMS
    if _ITEMS is None:
        _ITEMS = pd.read_parquet(PROC / "items_study.parquet").set_index("item_id")
    llm = _LLMS.setdefault(model, CacheOnly(model))
    it = _ITEMS.loc[item_id].to_dict(); it["item_id"] = item_id
    llm.log = []
    try:
        METHODS[method](llm, it, bundle(it, evidence) or bundle(it, "clean"))
    except Exception:
        return None
    for prompt, text in llm.log:
        if prompt.startswith("From the evidence"):
            return text
    return None

def tolerant_value(model, item_id, method, evidence):
    t = fact_text(model, item_id, method, evidence)
    m = VALUE_RE.search(t or "")
    return float(m.group(1)) if m else None
