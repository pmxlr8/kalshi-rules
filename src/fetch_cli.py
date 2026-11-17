import json, re, time
from datetime import date, timedelta
import requests
from config import RAW, IEM_AFOS, WINDOWS

PILS = ["CLINYC", "CLIMDW", "CLIMIA", "CLIAUS", "CLILAX", "CLIDEN", "CLIPHL"]
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
          "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

def parse_product(p):
    s = re.search(r"SUMMARY FOR ([A-Z]+) (\d+) (\d{4})", p)
    if not s:
        return None
    d = date(int(s.group(3)), MONTHS.index(s.group(1)) + 1, int(s.group(2)))
    issued = re.search(r"\n(\d{3,4} [AP]M [A-Z]{3} .*?\d{4})\n", p)
    mx = re.search(r"\n\s*MAXIMUM\s+(-?\d+|MM)", p)
    mn = re.search(r"\n\s*MINIMUM\s+(-?\d+|MM)", p)
    return {
        "date": d.isoformat(),
        "issued": issued.group(1) if issued else "",
        "final": "VALID TODAY AS OF" not in p,
        "max": mx.group(1) if mx else None,
        "min": mn.group(1) if mn else None,
        "text": p.strip(),
    }

def fetch_pil(pil, start, end):
    params = {"pil": pil, "fmt": "text", "limit": 9999, "sdate": start,
              "edate": (date.fromisoformat(end) + timedelta(days=3)).isoformat()}
    r = requests.get(IEM_AFOS, params=params, timeout=120)
    r.raise_for_status()
    prods = [parse_product(p) for p in r.text.split("\x01")[1:]]
    return [p for p in prods if p]

def main():
    start, end = WINDOWS["weather"]
    out = RAW / "cli"
    out.mkdir(parents=True, exist_ok=True)
    for pil in PILS:
        prods = fetch_pil(pil, start, end)
        by_day = {}
        for p in prods:
            if not (start <= p["date"] <= end):
                continue
            slot = by_day.setdefault(p["date"], {"final": None, "prelim": None})
            key = "final" if p["final"] else "prelim"
            if slot[key] is None:
                slot[key] = p
        with open(out / f"{pil}.json", "w") as f:
            json.dump(by_day, f)
        nf = sum(1 for v in by_day.values() if v["final"])
        print(f"{pil}: {len(prods)} products, {len(by_day)} days, {nf} with final report")
        time.sleep(1)

if __name__ == "__main__":
    main()
