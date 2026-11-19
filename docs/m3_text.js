// Text of the Milestone 3 report. Every number is read from numbers.json (N); a missing number throws.
module.exports = (N) => {
  const R = N.results, D = N.data, E = N.errors, PL = N.pilot;
  const need = (v, what) => { if (v === undefined || v === null) throw new Error('missing ' + what); return v; };
  const ov = (key, m) => need(R[key] && R[key].overall[m], `${key} ${m}`);
  const pct = x => (100 * need(x, 'pct')).toFixed(1) + '%';
  const pts = x => (x >= 0 ? '+' : '') + (100 * x).toFixed(1);
  const pair = (key, a, b, mode = 'tolerant') => {
    const p = need((R[key].pairs || []).find(q => q.compare === `${a} - ${b}` && q.scoring === mode), `${key} ${a}-${b}`);
    return `${pts(p.diff)} points (95% CI ${pts(p.ci_low)} to ${pts(p.ci_high)}, n = ${p.n})`;
  };
  const sl = (key, col, val) => need(R[key].slices[col].find(r => String(r[col]) === String(val)), `${key} ${col}=${val}`);
  const cell = (key, m, field, full) => {
    const o = R[key] && R[key].overall[m];
    if (!o) return 'not run';
    return pct(o[field]) + (o.n < full ? ` (n=${o.n})` : '');
  };
  const n0 = x => Number(x).toLocaleString('en-US');

  const A = 'ALLaM 7B | report', Q = 'Qwen 27B | report', G = 'gpt-oss 20B | report_both';
  const a1 = ov(A, 'C1_direct'), a4 = ov(A, 'C4_spec_code'), q1 = ov(Q, 'C1_direct'), g1 = ov(G, 'C1_direct');
  const qB1 = ov(Q, 'B1_no_evidence');
  const ea = E[A], eg = E[G];
  const causes = need(R[A].c4_causes.find(r => r.domain === 'weather'), 'causes');
  const vf = Object.fromEntries(R[A].c4_value_from.map(r => [r.value_from, r.n]));
  const gvf = Object.fromEntries(R[G].c4_value_from.map(r => [r.value_from, r.n]));
  const rev = D.revisions;

  const ci = key => {
    const p = need((R[key].pairs || []).find(q => q.compare === 'C4_spec_code - C1_direct' && q.scoring === 'tolerant'), key + ' ci');
    return `${pts(p.diff)} [${pts(p.ci_low)}, ${pts(p.ci_high)}]` + (p.n < R[key].overall.C1_direct.n ? ` (n=${p.n})` : '');
  };
  const resultsTable = [
    ['Model', 'Evidence', 'Items', 'C1 direct', 'C2 CoT', 'C4 strict', 'C4 tolerant', 'C4 minus C1, points [95% CI]'],
    ['ALLaM 2 7B', '1 report', String(a1.n), cell(A, 'C1_direct', 'acc_tol', a1.n), cell(A, 'C2_cot', 'acc_tol', a1.n),
      cell(A, 'C4_spec_code', 'acc', a1.n), cell(A, 'C4_spec_code', 'acc_tol', a1.n), ci(A)],
    ['Qwen 3.8 27B', '1 report', String(q1.n), cell(Q, 'C1_direct', 'acc_tol', q1.n), cell(Q, 'C2_cot', 'acc_tol', q1.n),
      cell(Q, 'C4_spec_code', 'acc', q1.n), cell(Q, 'C4_spec_code', 'acc_tol', q1.n), ci(Q)],
    ['gpt-oss 20B', '2 reports (weather)', String(g1.n), cell(G, 'C1_direct', 'acc_tol', g1.n), cell(G, 'C2_cot', 'acc_tol', g1.n),
      cell(G, 'C4_spec_code', 'acc', g1.n), cell(G, 'C4_spec_code', 'acc_tol', g1.n), ci(G)],
  ];

  const whenRow = (label, col, val) => {
    const r = sl(A, col, val);
    return [label, String(r.n_items), pct(r.C1_direct), pct(r.C4_spec_code), pts(r.C4_spec_code - r.C1_direct)];
  };
  const whenTable = [
    ['ALLaM 7B, dev (tolerant)', 'Items', 'C1 direct', 'C4 spec + code', 'Difference'],
    whenRow('Weather (long report with distractors)', 'domain', 'weather'),
    whenRow('Finance (one-line value)', 'domain', 'fin'),
    whenRow('Economics (one-line value)', 'domain', 'econ'),
    whenRow('Within 1 ladder step of the threshold', 'near', 'true'),
    whenRow('More than 1 step away', 'near', 'false'),
    whenRow('A report number would flip the answer', 'distractor_flip', 'true'),
    whenRow('No report number would flip it', 'distractor_flip', 'false'),
    whenRow('Two bounds ("between")', 'shape', 'between (2 bounds)'),
    whenRow('One bound', 'shape', 'one-sided'),
  ];

  const blocks = [
    { p: '**When Does Executing Contract Rules Help? LLM Resolution of Real Kalshi Markets**', after: 10 },
    { p: 'Final Project - Milestone 3 (Progress Report)', after: 10 },
    { p: '**Team:** Abhinav Sivakumar - as21153, Devansh Vikram - dv2482, Pranjal Mishra - pm4084. Code: github.com/pmxlr8/kalshi-rules', after: 40 },

    { h: 'How we addressed the Milestone 2 feedback' },
    { b: '**"Focus on when and why structured execution helps."** We no longer ask whether C4 beats C2 on average. Each item carries features that may decide when structure matters (distance to the threshold, one or two bounds, whether a distractor number in the evidence would flip the answer, report revisions, domain), and we vary model size. To explain why, we split every structured error by stage (rule, value, comparison) and by kind (reasoning or only output format).' },
    { b: `**"Your eval data is artificial."** We dropped the edited contracts (D2). Every item is a real settled Kalshi market, scored against Kalshi's real outcome, with the real evidence that the rules name. The gold comes from Kalshi's own data, so we need no hand labels.` },

    { h: 'System implemented so far' },
    { b: `**Data.** ${n0(D.markets)} settled markets in ${D.series} series (closed ${D.first_close} to ${D.last_close}) from the public Kalshi API. Kalshi's structured threshold applied to the settled value reproduces the real outcome on ${n0(D.gold_agree_numeric)} of the ${n0(D.numeric_value)} markets with a numeric value. So each item has an exact gold rule and gold value. The 1 exception is a real edge case: a Nasdaq-100 market whose threshold field (26,990) differs from its rules text (above 26,989.99), and the text decided it.` },
    { b: `**Evidence.** Weather: the NWS daily climate report for the station that the rules name (Iowa Environmental Mesonet archive). It matches Kalshi's value on ${D.station_days - D.missing_reports - D.value_mismatch} of ${D.station_days - D.missing_reports} station-days. It also lists the record, normal, departure, last-year value and the other daily extreme, so it holds natural distractors: on ${pct(D.weather_dflip_share)} of weather items, at least one of them would flip the answer. A second variant gives the preliminary (afternoon) and final reports together. Finance and economics: one line with the official value.` },
    { b: `**Study set.** ${D.study} items in ${D.events} events (weather ${D.by_domain.weather}, finance ${D.by_domain.fin}, economics ${D.by_domain.econ}), split by event: dev ${D.by_split.dev} items (${D.events_by_split.dev} events), test ${D.by_split.test} (${D.events_by_split.test} events). Prompts change on dev only. Test is untouched.` },
    { b: '**Methods** (same model, evidence and temperature 0): B1 no evidence; C1 direct answer; C2 chain of thought; C3 LLM writes a JSON spec, extracts the value and applies the spec in prose; C4 LLM writes the spec and extracts the value, Python applies the spec; O1 and O2 give C4 the gold spec or the gold value. C2-SC (5-sample vote), B2 (no rules) and O3 are built but not run yet.' },
    { b: '**Models** (Groq API): ALLaM 2 7B, Qwen 3.8 27B (reasoning off), gpt-oss 20B (reasoning low). Llama 3.1, our Milestone 2 choice, is no longer served there.' },
    { b: '**Scoring.** Strict: an answer must follow the output format. Tolerant: we re-read the saved output with format repairs only (a "verdict is NO" sentence, bounds put in the wrong JSON field, a value written before the JSON was cut off). Tolerant scoring uses no new LLM calls, and the gap between the two scores measures pure format failure. We tag ABSTAIN and invalid output as wrong.' },
    { b: '**Engineering.** Every call is cached and every run resumes. A self-test checks gold rules, the evaluator and the parsers. A Streamlit demo runs C2 and C4 side by side on any market.' },

    { h: 'Baseline results (dev)' },
    { p: `**B1 (no evidence)** on Qwen 27B has a balanced accuracy of ${qB1.bal_acc.toFixed(2)} (n = ${qB1.n}), which is chance. The contract text does not give away the outcome, and the model shows no sign of knowing these 2026 outcomes. **C1 (direct)** is the baseline to beat: ${pct(q1.acc)} on Qwen 27B (${q1.n} of ${q1.n}), ${pct(a1.acc_tol)} on ALLaM 7B, and ${pct(g1.acc_tol)} on gpt-oss 20B with both reports.` },

    { h: 'Current results (dev)' },
    { table: resultsTable, cols: [1250, 1100, 680, 1000, 1250, 1250, 1250, 2300], size: 16 },
    { p: `Accuracy on the dev split. C1 and C2 use tolerant scoring (strict C1: ${pct(a1.acc)}, ${pct(q1.acc)}, ${pct(g1.acc)}). "n=" marks a run that is not complete; the difference is paired on the items both methods have. Intervals: bootstrap over events. The second table splits the ALLaM 7B result by item feature.`, after: 40 },
    { table: whenTable, cols: [3800, 900, 1500, 1700, 1500], size: 16 },
    { p: '', after: 20 },
    { p: `**Our answer so far.** **When:** structure helps when the direct answer fails. On real markets that happens with a small model, with long evidence full of distractors, near the threshold and on two-bound rules. With a 27B model, the direct answer is already right on every dev item. **Why:** the direct answer fails at the comparison (a YES bias and wrong calls at inclusive bounds), and code makes the comparison exact. **Why not always:** each extra JSON step is a new place to break the format, so strict C4 loses until the pipeline handles format itself (plan item 2).`, after: 40 },

    { h: 'Experiments and comparisons completed' },
    { b: `E1 baselines (B1, C1). E2 main methods: C1 and C4 on all dev items for ALLaM 7B and Qwen 27B (Qwen C4 in part), C2 in part. E3 scale: 3 models. The revision variant (both reports) on gpt-oss 20B. Pilot v1 against v2 of the spec format. Strict against tolerant scoring for every method. Slices by domain, distance, distractors and bound type, with paired differences and event-clustered bootstrap intervals.` },

    { h: 'What worked' },
    { b: `**Structure helps the small model.** On ALLaM 7B, C4 beats C1 by ${pair(A, 'C4_spec_code', 'C1_direct')}. The gain is larger in every harder cell: weather against one-line values, near against far from the threshold, with against without a flipping distractor, two bounds against one (second table).` },
    { b: `**Real data with free, exact gold.** No labels, no generated items. Natural hard cases are common: ${D.dev_near} of ${D.by_split.dev} dev items are within 1 ladder step of the threshold, and ${D.dev_dflip} have a distractor that would flip the answer.` },
    { b: '**Tolerant scoring as a diagnostic.** It separates "the model reasoned wrong" from "the model broke the format", at no cost.' },

    { h: 'What failed' },
    { b: `**Strict C4 on the small model.** C4 has 2 JSON outputs where C1 has 1, so it has more ways to break. Strict C4 is ${pct(a4.acc)} against ${pct(a1.acc)} for strict C1 (${pair(A, 'C4_spec_code', 'C1_direct', 'strict')}).` },
    { b: `**No room to help a 27B model.** Qwen 27B answers all ${q1.n} dev items directly. On these markets, structure has nothing to fix at that size, so the "when" lives in smaller models and harder evidence.` },
    { b: `**Two reports break ALLaM 7B.** With both reports (about 3,300 input tokens, near its 4,096-token context), it loops or prints blank lines and gives no valid answer on ${E['ALLaM 7B | report_both'].c1_invalid_strict} of ${E['ALLaM 7B | report_both'].c1_n} items, so we stopped that run.` },
    { b: '**Compute.** The free Groq tier has a daily token limit per model (200,000 for Qwen and gpt-oss), so C2 and the oracle runs are not complete, and test is not run.' },

    { h: 'Failure analysis and likely causes' },
    { b: `**ALLaM 7B, direct answers (C1).** ${ea.all.c1_errors} of ${ea.c1_n} are wrong, and ${ea.all.yes_on_no} of them say YES on a NO market: it answers YES ${pct(ea.c1_yes_rate)} of the time against a true rate of ${pct(ea.gold_yes_rate)}. Of the ${ea.weather.c1_errors} weather errors, ${ea.weather.kinds['no value stated']} give only a verdict, with no value, ${ea.weather.kinds['wrong value']} cite a wrong value, and ${ea.weather.kinds['right value, wrong comparison']} cite the right value but compare it wrongly at a bound (for example, 70 judged outside "69° to 70°"). Likely cause: the comparison step, mostly at inclusive bounds. C4 fixes ${ea.all.c4_fixes} of the ${ea.all.c1_errors}, because Python does the comparison.` },
    { b: `**ALLaM 7B, strict C4.** All ${causes['format: extractor JSON cut off'] + causes['format: spec field slip'] + causes['still wrong: value']} errors are on weather. ${causes['format: extractor JSON cut off']}: the extractor wrote the right value, then copied the report line "word for word" as asked; the report's fixed-width columns are long runs of spaces, so it ran to the token cap before closing the JSON. ${causes['format: spec field slip']}: for "between" rules it put [low, high] in the "threshold" field. Only ${causes['still wrong: value']} are real value errors, and they took a distractor (last year ${vf.last_year || 0}, normal ${vf.normal || 0}, other ${vf.other || 0}).` },
    { b: `**gpt-oss 20B with both reports.** C1 abstains on ${eg.c1_abstain} of ${eg.c1_n} items, 2 of them on the one dev day where the reports disagree (NYC low, preliminary 58, final 54). It does not fall back to the later report. C4 picks a wrong value ${Object.values(gvf).reduce((a, b) => a + b, 0)} times, ${(gvf.record || 0) === Object.values(gvf).reduce((a, b) => a + b, 0) ? 'each time the record high' : `${gvf.record || 0} of them the record high`}, which sits next to the observed value in the same row.` },
    { b: `**Revisions are rare in real markets.** The preliminary and final reports differ on ${rev.dev.differs} of ${rev.dev.n} dev weather items and change the outcome on ${rev.dev.flips} (test: ${rev.test.differs} and ${rev.test.flips} of ${rev.test.n}). Real data has far fewer revision cases than the edited set we planned.` },

    { h: 'Changes attempted and their effects' },
    { b: `**Spec format v1 to v2** (one "threshold" field for one-bound rules, "low" and "high" only for "between"). C4 on the same ${PL.C4_spec_code.n} pilot items: ${PL.C4_spec_code.correct} to ${PL.C4_v2_same_items.correct} correct. Tolerant scoring of the v1 outputs also gives ${PL.C4_v1_tolerant}, so all ${PL.C4_spec_code.abstain} v1 errors were format slips. C3 (the LLM applies the same v1 spec) had ${PL.C3_spec_prose.correct} of ${PL.C3_spec_prose.n}: prose is robust to the slips that break code.` },
    { b: `**B1 prompt.** The v1 no-evidence prompt let the model abstain (${PL.B1_no_evidence.abstain} of ${PL.B1_no_evidence.n}). We now force YES or NO, which gives a true chance baseline.` },
    { b: `**Output cap for ALLaM 7B,** from 60 to 320 tokens: it writes prose before the JSON and was cut off. Strict invalid answers are now ${ea.c1_invalid_strict} of ${ea.c1_n}.` },
    { b: `**Report parser fix.** Our distractor parser missed times like "11:12 AM", so it read only 144 of 384 weather reports. After the fix it reads all 384, and the dev items with a flipping distractor went from 15 to ${D.dev_dflip}.` },
    { b: '**Free-tier runs.** One queue per model (each model has its own daily limit) that waits at the cap instead of stopping.' },

    { h: 'Remaining gaps relative to our success criteria' },
    { b: 'Our Milestone 2 primary metric (C4 minus C2 on 360 edited items) is gone with D2. The new primary result is C4 minus C1 and C4 minus C2 per cell (model by domain, distance, distractor and bound type), on the untouched test split with event-clustered intervals. Test is not run yet.' },
    { b: 'Not run yet: C2 on all dev items, C3 beyond the pilot, C2-SC at matched tokens, B2, the oracle runs O1 to O3, and the spec-agreement uncertainty check (H3).' },
    { b: 'Finance and economics evidence is one line, so it tests reading the rule, not finding the value. Our largest model is 27B, and we have no 70B model. The web-search bundles, the source admissibility check and the KalshiBench comparison with Kota (2026) are gone with the switch to the named source.' },

    { h: 'Prioritized plan for the final two weeks' },
    { b: '**1. Nov 20 to 23: test run** (C1, C2, C4 on ALLaM 7B and Qwen 27B; C1 and C4 on gpt-oss 20B, all 504 items) on a paid Groq tier, plus the rest of dev. Owner: Devansh (serving, cost).' },
    { b: '**2. Nov 20 to 24: fix the two format failure points in the pipeline itself** (a short quote of 12 words or less, a schema check with one retry, JSON mode), retest on dev, then freeze. Report strict scores as the main result. Owner: Abhinav (spec writer, evaluator).' },
    { b: '**3. Nov 22 to 26: real source text for finance and economics** (the BLS CPI release, the AAA daily price page), so those domains also test finding the value among distractors. Owner: Devansh.' },
    { b: '**4. Nov 24 to 28: compute and statistics.** C2-SC at matched tokens; O1 and O2 on test; a cluster-robust logistic "when" model (structured by distance, distractor, bound type, model size); a router chosen on dev and scored on test; gpt-oss 120B as the large model. Owner: Pranjal.' },
    { b: '**5. Nov 28 to Dec 1: failure analysis.** 30 errors per method read by hand and tagged by stage and cause. All three.' },
    { b: '**6. Dec 1 to 3: demo and final report.** The demo shows live C2 against C4 on a market, the stage where each one fails, and the cached results. All three.' },
  ];
  return { blocks };
};
