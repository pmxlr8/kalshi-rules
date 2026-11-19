#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
MODEL="${MODEL:-qwen/qwen3.8-27b}"
W="${WORKERS:-3}"
python3 run.py --model "$MODEL" --split dev --evidence report --methods C1_direct,C2_cot,C4_spec_code,C3_spec_prose,B1_no_evidence,B2_no_rules,O1_C4_gold_spec,O2_C4_gold_value --workers "$W"
python3 analysis.py --model "$MODEL" --evidence report
python3 run.py --model "$MODEL" --split test --evidence report --methods C1_direct,C2_cot,C4_spec_code --workers "$W"
python3 analysis.py --model "$MODEL" --evidence report
python3 run.py --model "$MODEL" --split test --evidence report --methods C3_spec_prose,B1_no_evidence,O1_C4_gold_spec,O2_C4_gold_value --workers "$W"
python3 analysis.py --model "$MODEL" --evidence report
