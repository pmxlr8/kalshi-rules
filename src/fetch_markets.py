import json, time
from datetime import datetime, timezone
import requests
from config import RAW, KALSHI, WEATHER, ECON, FIN, WINDOWS, domain_of

def ts(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())

def fetch_series(series):
    start, end = WINDOWS[domain_of(series)]
    params = {"series_ticker": series, "status": "settled", "limit": 1000,
              "min_close_ts": ts(start), "max_close_ts": ts(end) + 86400 * 2}
    out, cursor = [], None
    while True:
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{KALSHI}/markets", params=params, timeout=30)
        r.raise_for_status()
        d = r.json()
        out += d.get("markets", [])
        cursor = d.get("cursor")
        if not cursor:
            break
        time.sleep(0.3)
    return out

def main():
    (RAW / "markets").mkdir(parents=True, exist_ok=True)
    for s in WEATHER + ECON + FIN:
        ms = fetch_series(s)
        with open(RAW / "markets" / f"{s}.jsonl", "w") as f:
            for m in ms:
                f.write(json.dumps(m) + "\n")
        print(f"{s}: {len(ms)} markets, {len({m['event_ticker'] for m in ms})} events")

if __name__ == "__main__":
    main()
