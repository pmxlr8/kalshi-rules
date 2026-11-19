# When does executing contract rules help? LLM resolution of real Kalshi markets

NYU Generative AI Engineering, final project. Team: Abhinav Sivakumar, Devansh Vikram, Pranjal Mishra.

**Question.** When an LLM settles a prediction market, it must apply the contract's written rules to evidence.
We test when and why turning the rules into an executable spec (and letting Python apply it) is more reliable
than direct prompting or chain of thought, on **real** Kalshi markets with **real** evidence.

## Data
- **Contracts:** settled Kalshi markets pulled from the public API (`fetch_markets.py`): weather (7 cities, daily
  high and NYC low temperature), economics (CPI, payrolls, unemployment, Fed rate, GDP) and finance (S&P 500, gas prices).
  Each market has its rules text, outcome, threshold type (`greater`, `less`, `between`, ...) and settled value.
- **Gold:** Kalshi's structured threshold applied to the settled value reproduces the real outcome on 113,094 of the
  113,095 markets with a numeric settled value, and on all 666 study items (`build_items.py`, `selftest.py`). So every
  item has an exact gold spec and gold value, with no hand labels. 57 markets give only a text label and are left out.
  The 1 exception is a Nasdaq-100 market whose structured threshold (26,990) differs from its rules text
  ("above 26,989.99"); the text decided it.
- **Evidence:** for weather, the real NWS climate report (`fetch_cli.py`), which also lists the normal, record and
  last-year values and the other daily extreme (natural distractors). Its value matches Kalshi's settlement on
  366 of 367 station-days. `clean` evidence is a one-line official value; `report_both` gives the preliminary and
  final reports together (a natural revision case). Finance and economics items use `clean` evidence.
- **Study sample:** 666 items (384 weather, 144 finance, 138 economics), dev 162 / test 504, split by event (`sample.py`).

## Methods (`methods.py`)
| Method | What the LLM does | What code does | LLM calls |
|---|---|---|---|
| B1_no_evidence | Guesses from the contract only | Parse | 1 |
| B2_no_rules | Sees evidence and title, no rules text | Parse | 1 |
| C1_direct | Reads rules and evidence, answers | Parse | 1 |
| C2_cot | Reasons step by step, answers | Parse | 1 |
| C2SC_cot_vote5 | 5 sampled chains of thought | Majority vote | 5 |
| C3_spec_prose | Writes spec, extracts value, applies spec in prose | Nothing | 3 |
| C4_spec_code | Writes spec, extracts value | Applies the spec | 2 |
| O1_C4_gold_spec | Extracts value only (gold spec given) | Applies the spec | 1 |
| O2_C4_gold_value | Writes spec only (gold value given) | Applies the spec | 1 |
| O3_C2_gold_spec_text | Chain of thought with the gold spec in the prompt | Parse | 1 |

The oracle swaps (O1 to O3) split every error into **reading the rule**, **finding the value** or **applying the rule**.

## "When" features (`features.py`)
Threshold type, distance to the threshold in ladder steps (`near` = within 1 step), domain, whether a distractor
number in the report would flip the answer (`distractor_flip`), departure from normal, and prior conflict
(the no-evidence answer B1 is wrong).

## Run
```bash
pip install -r requirements.txt
cp .env.example .env                   # then paste your key after GROQ_API_KEY= (never commit .env)
cd src && python3 preflight.py         # checks the key and the model, makes 1 test call
cd .. && SPLITS=dev ./run_all.sh       # tune prompts on dev only
SPLITS=test ./run_all.sh               # then run test once
```
`MODEL=<groq model id>` picks another model. Every call is cached in `runs/cache.jsonl`, and runs resume.
Per-item outputs go to `runs/<model>/<evidence>/<method>.jsonl`. Tables and figures go to
`results/<model>/<evidence>/` (`summary.md`, accuracy vs. distance to threshold, C4 vs. C2 gain by cell,
a cluster-robust "when" regression, stage error budget, and a router learned on dev and scored on test).
`python3 run.py --fake ...` tests the plumbing without an API key.

## Rebuild the data from scratch
```bash
cd src
python3 fetch_markets.py && python3 fetch_cli.py && python3 build_items.py
python3 check_evidence.py && python3 sample.py && python3 features.py && python3 selftest.py
```
