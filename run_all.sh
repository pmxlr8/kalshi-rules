#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
MODEL="${MODEL:-llama-3.1-8b-instant}"
SPLITS="${SPLITS:-dev}"
WORKERS="${WORKERS:-8}"
REPORT_METHODS="B1_no_evidence,B2_no_rules,C1_direct,C2_cot,C2SC_cot_vote5,C3_spec_prose,C4_spec_code,O1_C4_gold_spec,O2_C4_gold_value,O3_C2_gold_spec_text"
CLEAN_METHODS="C1_direct,C2_cot,C4_spec_code"

python3 preflight.py "$MODEL"
python3 features.py
for SPLIT in $SPLITS; do
  python3 run.py --model "$MODEL" --split "$SPLIT" --evidence report --methods "$REPORT_METHODS" --workers "$WORKERS"
  python3 run.py --model "$MODEL" --split "$SPLIT" --evidence clean --domains weather --methods "$CLEAN_METHODS" --workers "$WORKERS"
  python3 run.py --model "$MODEL" --split "$SPLIT" --evidence report_both --domains weather --methods "$CLEAN_METHODS" --workers "$WORKERS"
done
for EV in report clean report_both; do
  python3 analysis.py --model "$MODEL" --evidence "$EV"
done
