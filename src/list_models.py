from llm import LLM

if __name__ == "__main__":
    for m in sorted(x.id for x in LLM("none").client.models.list().data):
        print(m)
