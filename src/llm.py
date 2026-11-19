import hashlib, json, os, random, re, threading, time
from collections import deque
from openai import OpenAI, RateLimitError, APIError
from config import ROOT, RUNS, REASONING, MIN_COMPLETION

def load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

class Cache:
    def __init__(self, path):
        self.path, self.lock, self.mem = path, threading.Lock(), {}
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            for line in path.open():
                d = json.loads(line)
                self.mem[d["key"]] = d["val"]

    def get(self, key):
        return self.mem.get(key)

    def put(self, key, val):
        with self.lock:
            self.mem[key] = val
            with self.path.open("a") as f:
                f.write(json.dumps({"key": key, "val": val}) + "\n")

class TokenLimiter:
    def __init__(self, tpm):
        self.tpm, self.lock, self.log = tpm, threading.Lock(), deque()

    def wait(self, est):
        if not self.tpm:
            return
        while True:
            with self.lock:
                now = time.time()
                while self.log and now - self.log[0][0] > 60:
                    self.log.popleft()
                used = sum(t for _, t in self.log)
                if used + est <= self.tpm:
                    self.log.append((now, est))
                    return
            time.sleep(1.0)

LIMITERS = {}

def wait_seconds(msg):
    """Parse Groq's 'try again in 1h2m3.4s' (or '850ms') into seconds. None if absent."""
    m = re.search(r"try again in ((?:[\d.]+h)?(?:[\d.]+m(?!s))?(?:[\d.]+s)?(?:[\d.]+ms)?)", msg)
    if not m or not m.group(1):
        return None
    total = 0.0
    for num, unit in re.findall(r"([\d.]+)(ms|h|m|s)", m.group(1)):
        total += float(num) * {"h": 3600, "m": 60, "s": 1, "ms": 0.001}[unit]
    return total

class LLM:
    def __init__(self, model, base_url=None, key_env="GROQ_API_KEY", cache_path=RUNS / "cache.jsonl"):
        load_env()
        self.model = model
        self.client = OpenAI(base_url=base_url or os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                             api_key=os.environ.get(key_env, "missing"))
        self.cache = Cache(cache_path)
        tpm = int(os.environ.get("LLM_TPM", "0"))
        self.limiter = LIMITERS.setdefault(model, TokenLimiter(tpm))

    def chat(self, messages, temperature=0.0, max_tokens=400, sample=0):
        effort = REASONING.get(self.model)
        max_tokens = max(max_tokens, MIN_COMPLETION.get(self.model, 0))
        key = hashlib.sha256(json.dumps([self.model, messages, temperature, max_tokens, sample, effort]).encode()).hexdigest()
        hit = self.cache.get(key)
        if hit:
            return {**hit, "cached": True}
        extra = {"reasoning_effort": effort} if effort else {}
        est = int(len(json.dumps(messages)) / 3.2) + 20
        for attempt in range(40):
            try:
                self.limiter.wait(est)
                t0 = time.time()
                r = self.client.chat.completions.create(model=self.model, messages=messages,
                                                        temperature=temperature, max_tokens=max_tokens,
                                                        seed=sample, extra_body=extra)
                val = {"text": r.choices[0].message.content or "",
                       "in_tok": r.usage.prompt_tokens, "out_tok": r.usage.completion_tokens,
                       "latency": round(time.time() - t0, 3)}
                self.cache.put(key, val)
                return {**val, "cached": False}
            except (RateLimitError, APIError) as e:
                msg = str(e)
                daily = "per day" in msg or "(TPD)" in msg or "(RPD)" in msg
                if daily and os.environ.get("LLM_WAIT_DAILY") == "1":
                    # free tier: the daily bucket refills slowly, so wait and retry instead of stopping
                    wait = min(max(wait_seconds(msg) or 300, 30), 1800)
                    print(f"  daily cap, waiting {wait:.0f}s", flush=True)
                    time.sleep(wait + random.uniform(1, 10))
                    continue
                if daily or attempt == 39:
                    raise
                wait = wait_seconds(msg)
                wait = wait if wait is not None else min(60, 2 ** min(attempt, 5))
                time.sleep(wait + random.uniform(0.5, 2.0))
