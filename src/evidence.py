import json, re
from functools import lru_cache
from config import RAW

@lru_cache(maxsize=None)
def cli_days(pil):
    with open(RAW / "cli" / f"{pil}.json") as f:
        return json.load(f)

def trim_cli(text):
    cut = re.search(r"\n\s*DEGREE DAYS", text)
    return text[:cut.start()].rstrip() if cut else text

def weather_report(item, version="final"):
    pil = item["station"]
    if pil == "CLICHI":
        pil = "CLIMDW"
    day = cli_days(pil).get(item["obs_date"]) or {}
    prod = day.get(version)
    return (trim_cli(prod["text"]), prod) if prod else (None, None)

def clean_statement(item):
    if item["domain"] == "weather":
        return f"Official reading: the {item['measure']} temperature on {item['obs_date']} was {item['expiration_value']}°F."
    return f"Official reading for this contract's measured quantity: {item['expiration_value']}."

def bundle(item, kind):
    if kind == "clean":
        return clean_statement(item)
    if kind == "report" and item["domain"] == "weather":
        text, _ = weather_report(item)
        return text
    if kind == "report_both" and item["domain"] == "weather":
        return bundle_both(item)
    return None

ROW = re.compile(r"\n\s*{name}\s+(-?\d+|MM)\s+(?:\d{{1,4}}\s+[AP]M\s+)?(-?\d+|MM)R?\s+(\d{{4}})\s+(-?\d+|MM)\s+(-?\d+|MM)\s+(-?\d+|MM)")

def _n(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def cli_numbers(item):
    text, _ = weather_report(item)
    if not text:
        return {}
    out = {}
    for name in ("MAXIMUM", "MINIMUM"):
        m = re.search(ROW.pattern.format(name=name), text)
        if m:
            out[name.lower()] = {"observed": _n(m.group(1)), "record": _n(m.group(2)), "normal": _n(m.group(4)),
                                 "departure": _n(m.group(5)), "last_year": _n(m.group(6))}
    return out

def bundle_both(item):
    final, _ = weather_report(item, "final")
    prelim, _ = weather_report(item, "prelim")
    if not (final and prelim):
        return None
    return f"REPORT A (issued first):\n{prelim}\n\nREPORT B (issued later):\n{final}"
