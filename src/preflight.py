import os, sys
from llm import LLM, load_env

def main(model):
    load_env()
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit("No key: open kalshi_rules/.env and paste your key after GROQ_API_KEY=")
    llm = LLM(model)
    ids = sorted(m.id for m in llm.client.models.list().data)
    if model not in ids:
        print("Model not served. Available models:\n  " + "\n  ".join(ids))
        sys.exit(f"Set MODEL to one of the ids above, e.g. MODEL=<id> ./run_all.sh")
    r = llm.chat([{"role": "user", "content": "Reply with the word ok."}], max_tokens=5)
    print(f"key works, model {model} answered: {r['text'].strip()!r} ({r['latency']}s)")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MODEL", "llama-3.1-8b-instant"))
