import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
RUNS = ROOT / "runs"

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
IEM_AFOS = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"

WEATHER = ["KXHIGHNY", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHAUS", "KXHIGHLAX", "KXHIGHDEN", "KXHIGHPHIL", "KXLOWTNYC"]
ECON = ["KXCPI", "KXCPIYOY", "KXCPICORE", "KXPAYROLLS", "KXU3", "KXFED", "KXGDP", "KXEGGS"]
FIN = ["KXINX", "KXINXU", "KXNASDAQ100U", "KXAAAGASW", "KXAAAGASD"]

WINDOWS = {
    "weather": ("2026-10-01", "2026-11-15"),
    "econ": ("2026-01-01", "2026-11-15"),
    "fin": ("2026-10-01", "2026-11-15"),
}

def domain_of(series):
    if series in WEATHER:
        return "weather"
    if series in ECON:
        return "econ"
    return "fin"

DEFAULT_MODEL = "qwen/qwen3.8-27b"
REASONING = {"qwen/qwen3.8-27b": "none", "openai/gpt-oss-20b": "low", "openai/gpt-oss-120b": "low"}
MIN_COMPLETION = {"openai/gpt-oss-20b": 1024, "openai/gpt-oss-120b": 1024}

def slug(model):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", model)
