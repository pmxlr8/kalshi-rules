#!/usr/bin/env bash
# Dev-split runs that fit the Groq free tier. Each model has its own daily token bucket,
# so the three queues run in parallel. LLM_WAIT_DAILY=1 makes a queue wait when its
# daily cap is hit, instead of stopping. Every call is cached, so a rerun resumes.
set -uo pipefail
cd "$(dirname "$0")/src"
export LLM_WAIT_DAILY=1
PY="${PY:-python3}"

(   # 7B model: is the direct answer still reliable when the model is small?
    export LLM_TPM=5500; M=allam-2-7b
    $PY run.py --model $M --split dev --evidence report --methods C1_direct,C4_spec_code --workers 3
    $PY run.py --model $M --split dev --domains weather --evidence report_both --methods C1_direct,C4_spec_code --workers 3
    $PY run.py --model $M --split dev --evidence report --methods C2_cot,O1_C4_gold_spec,O2_C4_gold_value,C3_spec_prose --workers 3
    $PY run.py --model $M --split dev --domains weather --evidence report_both --methods C2_cot --workers 3
) > ../runs/free_allam.log 2>&1 &

(   # 27B model: finish the dev comparison on report evidence
    export LLM_TPM=7500; M=qwen/qwen3.8-27b
    $PY run.py --model $M --split dev --evidence report --methods C4_spec_code,C2_cot,O1_C4_gold_spec,O2_C4_gold_value --workers 2
) > ../runs/free_qwen.log 2>&1 &

(   # reasoning model: does a revised report (preliminary + final) break the direct answer?
    export LLM_TPM=7500; M=openai/gpt-oss-20b
    $PY run.py --model $M --split dev --domains weather --evidence report_both --methods C1_direct,C4_spec_code --workers 2
    $PY run.py --model $M --split dev --domains weather --evidence report --methods C1_direct,C4_spec_code --workers 2
) > ../runs/free_gptoss.log 2>&1 &

wait
for M in allam-2-7b qwen/qwen3.8-27b openai/gpt-oss-20b; do
    for E in report report_both; do $PY analysis.py --model $M --evidence $E || true; done
done
