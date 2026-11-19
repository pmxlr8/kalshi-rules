import json
import pandas as pd
import streamlit as st
from config import PROC, DEFAULT_MODEL
from evidence import bundle
from methods import METHODS, gold_spec
from llm import LLM

st.set_page_config(page_title="Kalshi rule resolution", layout="wide")
st.title("Does executing the rules help? Chain of thought vs. spec + code")

items = pd.read_parquet(PROC / "items_study_feat.parquet")
with st.sidebar:
    model = st.text_input("Model", DEFAULT_MODEL)
    domain = st.selectbox("Domain", sorted(items.domain.unique()))
    sub = items[items.domain == domain]
    only_hard = st.checkbox("Only near-threshold items", value=False)
    if only_hard:
        sub = sub[sub.near]
    item_id = st.selectbox("Market", sub.item_id.tolist())
    evidence = st.radio("Evidence", ["report", "clean", "report_both"] if domain == "weather" else ["clean"])

it = items[items.item_id == item_id].iloc[0].to_dict()
ev = bundle(it, evidence) or bundle(it, "clean")

left, right = st.columns(2)
with left:
    st.subheader("Contract")
    st.markdown(f"**{it['title']}**  \nYES label: {it['yes_sub_title']}")
    st.caption(it["rules_primary"])
    st.subheader("Evidence")
    st.code(ev, language=None)
with right:
    st.subheader("Gold (from Kalshi)")
    st.json({"settled value": it["value"], "outcome": it["result"].upper(), "gold spec": gold_spec(it)})
    if st.button("Run both methods"):
        llm = LLM(model)
        c2 = METHODS["C2_cot"](llm, it, ev)
        c4 = METHODS["C4_spec_code"](llm, it, ev)
        a, b = st.columns(2)
        with a:
            st.markdown(f"### C2 chain of thought: {c2['verdict']} {'✅' if c2['verdict'] == it['result'].upper() else '❌'}")
            st.write(c2["raw"])
            st.caption(f"{c2['calls']} call, {c2['in_tok'] + c2['out_tok']} tokens")
        with b:
            st.markdown(f"### C4 spec + code: {c4['verdict']} {'✅' if c4['verdict'] == it['result'].upper() else '❌'}")
            st.json({"LLM spec": c4["spec"], "extracted value": c4["value"], "quote": c4["quote"]})
            st.caption(f"{c4['calls']} calls, {c4['in_tok'] + c4['out_tok']} tokens")
