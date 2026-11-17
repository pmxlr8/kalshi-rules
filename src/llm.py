import hashlib, json, os, threading, time
from openai import OpenAI, RateLimitError, APIError
from config import ROOT, RUNS

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

class LLM:
    def __init__(self, model, base_url=None, key_env="GROQ_API_KEY", cache_path=RUNS / "cache.jsonl"):
        load_env()
        self.model = model
        self.client = OpenAI(base_url=base_url or os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                             api_key=os.environ.get(key_env, "missing"))
        self.cache = Cache(cache_path)

    def chat(self, messages, temperature=0.0, max_tokens=400, sample=0):
        key = hashlib.sha256(json.dumps([self.model, messages, temperature, max_tokens, sample]).encode()).hexdigest()
        hit = self.cache.get(key)
        if hit:
            return {**hit, "cached": True}
        for attempt in range(6):
            try:
                t0 = time.time()
                r = self.client.chat.completions.create(model=self.model, messages=messages,
                                                        temperature=temperature, max_tokens=max_tokens,
                                                        seed=sample)
                val = {"text": r.choices[0].message.content or "",
                       "in_tok": r.usage.prompt_tokens, "out_tok": r.usage.completion_tokens,
                       "latency": round(time.time() - t0, 3)}
                self.cache.put(key, val)
                return {**val, "cached": False}
            except (RateLimitError, APIError) as e:
                if attempt == 5:
                    raise
                time.sleep(min(60, 2 ** attempt * 2))
