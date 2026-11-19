// Milestone 3 report: HTML -> PDF (Chrome headless). Every number comes from results/m3/numbers.json;
// a missing number stops the build. Run: python3 src/m3_report.py && python3 src/audit_c4.py &&
// python3 src/m3_numbers.py && python3 src/m3_figure.py && node docs/make_m3_pdf.js
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { pathToFileURL } = require('url');

const ROOT = path.join(__dirname, '..');
const N = JSON.parse(fs.readFileSync(path.join(ROOT, 'results', 'm3', 'numbers.json'), 'utf8'));
const FIG = fs.readFileSync(path.join(__dirname, 'm3_fig.svg'), 'utf8').replace(/^[\s\S]*?(<svg)/, '$1');
const R = N.results, D = N.data, E = N.errors, PL = N.pilot, H = N.hand;

const need = (v, what) => { if (v === undefined || v === null) throw new Error('missing ' + what); return v; };
const ov = (key, m) => need(R[key] && R[key].overall[m], `${key} ${m}`);
const pct = x => (100 * need(x, 'pct')).toFixed(1) + '%';
const num = x => (100 * x).toFixed(1);
const sgn = x => (x < 0 ? '−' : '') + Math.abs(100 * x).toFixed(1);
const n0 = x => Number(x).toLocaleString('en-US');
const pairOf = (key, a, b, mode = 'strict') => need((R[key].pairs || []).find(q => q.compare === `${a} - ${b}` && q.scoring === mode), `${key} ${a}-${b} ${mode}`);
const ci = p => `${sgn(p.diff)} [${sgn(p.ci_low)}, ${sgn(p.ci_high)}]`;
const cell = (key, m, field, full) => { const o = R[key] && R[key].overall[m]; return o ? pct(o[field]) + (o.n < full ? ` (${o.n})` : '') : '-'; };

const A = 'ALLaM 7B | report', Q = 'Qwen 27B | report', G1 = 'gpt-oss 20B | report', G2 = 'gpt-oss 20B | report_both';
const a1 = ov(A, 'C1_direct'), a2 = ov(A, 'C2_cot'), a3 = ov(A, 'C3_spec_prose'), a4 = ov(A, 'C4_spec_code');
const aO1 = ov(A, 'O1_C4_gold_spec'), aO2 = ov(A, 'O2_C4_gold_value');
const q1 = ov(Q, 'C1_direct'), q4 = ov(Q, 'C4_spec_code'), qB1 = ov(Q, 'B1_no_evidence');
const g1 = ov(G1, 'C1_direct'), g4 = ov(G1, 'C4_spec_code'), gb1 = ov(G2, 'C1_direct');
const ea = E[A], eg1 = E[G1], eg2 = E[G2], eab = E['ALLaM 7B | report_both'];
const hc = H.c1_allam_weather, hr = H.c4_allam_repairs, hl = hc.labels;
const wrongVal = Object.entries(hl).filter(([k]) => k.startsWith('wrong value')).reduce((s, [, v]) => s + v, 0);
const vf = Object.fromEntries(R[A].c4_value_from.map(r => [r.value_from, r.n]));
const gvf1 = Object.fromEntries(R[G1].c4_value_from.map(r => [r.value_from, r.n]));
const gvf2 = Object.fromEntries(R[G2].c4_value_from.map(r => [r.value_from, r.n]));
const rev = D.revisions;
const pA = pairOf(A, 'C4_spec_code', 'C1_direct'), pAt = pairOf(A, 'C4_spec_code', 'C1_direct', 'tolerant');
const pQ = pairOf(Q, 'C4_spec_code', 'C1_direct'), pG1 = pairOf(G1, 'C4_spec_code', 'C1_direct'), pG2 = pairOf(G2, 'C4_spec_code', 'C1_direct');
const p34 = pairOf(A, 'C3_spec_prose', 'C4_spec_code');
const sh = key => need(R[key].shared_c1_c4, key + ' shared');
const diffCell = (key, p) => (p.diff === 0 && p.ci_low === 0 && p.ci_high === 0) ? `0.0, no item differs (${p.n})` : ci(p) + (p.n < R[key].overall.C1_direct.n ? ` (${p.n})` : '');
const row = (name, ev, key, full, p) => `<tr><td>${name}</td><td>${ev}</td><td class="r">${full}</td><td class="r">${cell(key, 'C1_direct', 'acc', full)}</td><td class="r">${cell(key, 'C2_cot', 'acc', full)}</td><td class="r">${cell(key, 'C3_spec_prose', 'acc', full)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc', full)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc_tol', full)}</td><td class="r">${diffCell(key, p)}</td></tr>`;
const name = { last_year: "last year's value", normal: 'the normal', record: 'the record high', other: 'a number that is in neither the report nor the rule', 'no value': 'no value' };
const valueList = Object.entries(vf).map(([k, v]) => `${name[k] || k} (${v})`).join(', ');
const c3Weather = R[A].slices.domain.find(r => r.domain === 'weather');
const gFlip = R[G1].slices.distractor_flip.find(r => String(r.distractor_flip).toLowerCase() === 'true');
const dev = D.by_split.dev;

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Milestone 3 Progress Report</title><style>
@page { size: Letter; margin: 0.65in 0.7in; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 9.4pt; line-height: 1.3; color: #000; margin: 0; }
h1 { font-size: 14pt; margin: 0 0 2px; }
.sub { margin: 0 0 1px; }
h2 { font-size: 10.8pt; margin: 10px 0 3px; break-after: avoid; }
p { margin: 0 0 5px; text-align: left; }
ul, ol { margin: 0 0 5px; padding-left: 20px; }
li { margin: 0 0 2px; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 4px 0 3px; break-inside: avoid; }
th, td { border: 1px solid #999; padding: 2px 4px; vertical-align: top; }
th { background: #e8e8e8; text-align: left; }
.r { text-align: right; }
.cap { font-size: 8.5pt; margin: 0 0 7px; }
figure { margin: 6px 0 2px; break-inside: avoid; }
figure svg { width: 100%; height: auto; display: block; }
figure svg text { font-family: Arial, Helvetica, sans-serif !important; }
</style></head><body>

<h1>Milestone 3: Progress Report</h1>
<p class="sub"><b>When Does Executing Contract Rules Help? LLM Resolution of Real Kalshi Markets</b></p>
<p class="sub">Team: Abhinav Sivakumar (as21153), Devansh Vikram (dv2482), Pranjal Mishra (pm4084)</p>
<p class="sub" style="margin-bottom:6px">Code: https://github.com/pmxlr8/kalshi-rules</p>

<h2>Response to the Milestone 2 feedback</h2>
<p>We were asked to focus on when and why structured execution helps, not on showing that C4 wins, and we were told that our edited contracts were artificial. We dropped the edited contracts. We now use only real settled Kalshi markets, with the evidence source that the rules name and Kalshi's outcome as the label. We break results down by model and by item properties (distance to the threshold, a number in the evidence that would flip the answer, one or two bounds), and we use oracle runs and item-level audits to find which pipeline step causes each error. So far the answer to "when" is narrow: under strict scoring, structure has not beaten the direct answer for any model.</p>

<h2>1. System implemented so far</h2>
<p><b>Data.</b> We pulled ${n0(D.markets)} settled markets from ${D.series} series through Kalshi's public API (closed between ${D.first_close} and ${D.last_close}). Each market has its rules text, the outcome, a structured threshold and the final value. Applying the threshold to the final value gives back Kalshi's outcome on ${n0(D.gold_agree_numeric)} of the ${n0(D.numeric_value)} markets with a numeric value, so we get labels without hand annotation (the one mismatch is a Nasdaq-100 market where the threshold field and the rules text differ by 0.01).</p>
<p><b>Evidence.</b> For weather we use the NWS daily climate report for the station in the rules, the source Kalshi settles on. The weather markets use ${D.station_date_measure_values} values (one per station, date and daily high or low). We found the report for ${D.station_date_measure_values - D.missing_reports} of them, and it matches Kalshi's value on ${D.station_date_measure_values - D.missing_reports - D.value_mismatch}. The report also lists the record, the normal, the departure from normal, last year's value and the other daily extreme, so the model has to pick the right number; on ${Math.round(100 * D.weather_dflip_share)}% of weather items at least one of these would flip the answer. A second version has both the preliminary and the final report. Finance and economics evidence is one line with the official value.</p>
<p><b>Study set.</b> ${D.study} markets from ${D.events} events (${D.by_domain.weather} weather, ${D.by_domain.fin} finance, ${D.by_domain.econ} economics), split by event into dev (${dev} items, ${D.events_by_split.dev} events) and test (${D.by_split.test} items, ${D.events_by_split.test} events). We only change prompts based on dev.</p>
<p><b>Methods.</b> All methods use the same model, evidence and temperature 0. B1 sees the contract but no evidence. C1 answers directly. C2 uses chain of thought. C3 writes a JSON spec of the rule, extracts the value and applies the spec in text. C4 does the same spec and extraction, but Python applies the spec. O1 is C4 with the gold spec, and O2 is C4 with the gold value, to locate errors. We run three models through the Groq API: ALLaM 2 7B, Qwen 3.8 27B (reasoning off) and gpt-oss 20B (low reasoning). Llama 3.1 (planned in Milestone 2) is no longer on Groq.</p>
<p><b>Scoring.</b> Strict scoring requires the exact output format and is our main result, because it is what a deployed system would get. We also report a tolerant score, which estimates performance after deterministic post-processing of common schema and serialization errors: a verdict written as a sentence, a value read from an extractor reply whose JSON was cut off, and the two bounds of a "between" rule written as a list in the threshold field. It re-reads the saved outputs with no new model calls. A repair can also change an answer that was wrong for other reasons, so the gap is not a pure count of format errors (results/m3/c4_repairs.csv lists every repaired C4 item). The repository has every per-item output, the model-call cache (all tables rebuild without API calls), Parquet data and pinned package versions.</p>

<h2>2. Baseline results</h2>
<p>Without evidence (B1), Qwen 27B was run on ${qB1.n} of ${dev} dev items before the daily limit. Its raw accuracy is ${pct(qB1.acc)}, but ${pct(N.b1.gold_no_share)} of these items resolve NO and the model answers NO on ${pct(N.b1.pred_no_share)} of them, so its balanced accuracy is ${qB1.bal_acc.toFixed(2)}. This fits the outcome not being inferable from the contract alone, but one model on ${qB1.n} items cannot rule out that a model knows some outcomes. The direct answer (C1) is our main baseline (Table 1).</p>

<div style="break-inside: avoid"><h2>3. Current results</h2>
<table>
<tr><th>Model</th><th>Evidence</th><th class="r">Items</th><th class="r">C1</th><th class="r">C2</th><th class="r">C3</th><th class="r">C4</th><th class="r">C4 tolerant</th><th class="r">C4 minus C1, strict [95% CI]</th></tr>
${row('ALLaM 2 7B', '1 report', A, dev, pA)}
${row('Qwen 3.8 27B', '1 report', Q, dev, pQ)}
${row('gpt-oss 20B', '1 report', G1, g1.n, pG1)}
${row('gpt-oss 20B', '2 reports', G2, gb1.n, pG2)}
</table>
<p class="cap">Table 1. Dev accuracy, strict scoring unless marked; "-" is not run yet; (n) is items run so far. gpt-oss rows: weather dev items plus 2 others (1 report), weather only (2 reports). Differences in points, paired on shared items; 95% CI from a bootstrap over events.</p></div>
<figure>${FIG}</figure>
<p class="cap">Figure 1. (A) Strict dev accuracy of C1 and C4 on the items that have both; the open circle is C4 with tolerant scoring. (B) ALLaM 7B, C1 against C4 by item type, both with tolerant scoring; n per row in brackets.</p>
<p><b>Under strict scoring, C4 has not beaten the direct answer for any model.</b> For ALLaM 7B, C4 is ${num(-pA.diff)} points worse than C1 (${ci(pA)}). For gpt-oss 20B the difference is ${ci(pG1)} with one report and ${ci(pG2)} with two. On the ${pQ.n} Qwen 27B items completed so far, both C1 and C4 are correct on every item, so the run does not show an advantage for C4.</p>
<p><b>After format repair, C4 helps the small model.</b> With tolerant scoring, C4 is ${num(pAt.diff)} points better than C1 for ALLaM 7B (${ci(pAt)}), and the gain is largest on weather items, items near the threshold and items with a flipping distractor (Figure 1B). The oracle runs show where its strict errors come from. With the gold value (O2), ALLaM's own spec gives ${pct(aO2.acc)} strict and ${pct(aO2.acc_tol)} tolerant, so after the list repair its spec gives the right outcome for the true value on all ${dev} items. With the gold spec (O1), it gives ${pct(aO1.acc)} strict and ${pct(aO1.acc_tol)} tolerant, so the strict loss there comes from cut-off extractor replies, and only ${Math.round((1 - aO1.acc_tol) * aO1.n)} extracted values are wrong.</p>

<h2>4. Experiments and comparisons completed</h2>
<p>ALLaM 7B: C1, C2, C3, C4, O1 and O2 on all ${dev} dev items. Qwen 27B: C1 on all dev items, C4 on ${q4.n} (1 item failed on an empty API reply), C2 on ${ov(Q, 'C2_cot').n} so far, B1 on ${qB1.n}. gpt-oss 20B: C1 and C4 on the weather dev items with one and with two reports. A 12-item pilot compared two spec formats. We hand-checked all ${hc.n} wrong ALLaM C1 answers on weather (results/m3/c1_weather_errors_handlabels.csv) and audited all ${hr.strict_errors} strict C4 errors (results/m3/c4_repairs.csv).</p>

<h2>5. What worked</h2>
<ul>
<li>Real markets: exact labels from Kalshi and many hard cases (${D.dev_near} of ${dev} dev items within one step of the threshold, ${D.dev_dflip} with a flipping distractor).</li>
<li>Oracle runs and item audits: they separate spec meaning, value extraction and output format, the "why" part of our question.</li>
<li>Moving the comparison to code: the comparison is where the small model's direct answers fail (Section 7).</li>
</ul>

<h2>6. What failed</h2>
<ul>
<li>Strict C4 on ALLaM 7B is worse than the direct answer (${pct(a4.acc)} against ${pct(a1.acc)}). C3, which applies the spec in text, is no better (${pct(a3.acc)}, ${ci(p34)} against C4) and gets only ${pct(c3Weather.C3_spec_prose)} on weather: it gives no answer on ${pct(a3.no_answer)} of items, all of them items where the extractor returned no usable value.</li>
<li>With both reports (about 3,300 input tokens, close to its 4,096-token limit), ALLaM 7B repeated itself or printed blank lines and gave no valid answer on ${eab.c1_invalid_strict} of ${eab.c1_n} items, so we stopped that run.</li>
<li>Qwen 27B is at or near 100% on dev, so these items cannot show a benefit of structure for it. Groq's free-tier daily limits stopped the test set and some dev runs.</li>
</ul>

<h2>7. Failure analysis and likely causes</h2>
<p><b>ALLaM 7B, direct answers.</b> ${ea.all.c1_errors} of ${ea.c1_n} answers are wrong (tolerant), and ${ea.all.yes_on_no} of these say YES when the answer is NO; it answers YES ${pct(ea.c1_yes_rate)} of the time while the true rate is ${pct(ea.gold_yes_rate)}. We read all ${hc.n} wrong weather answers. ${hl['verdict only']} give only a verdict with no reasoning, all YES on Chicago items; on ${hc.all_yes_days.length} Chicago days the model said YES to all ${hc.all_yes_items / hc.all_yes_days.length} buckets of the same day, although only one can be true. ${hl['right value wrong comparison']} state the right value but compare it wrongly (for example, 70 is "not" in "69&deg; to 70&deg;"). ${wrongVal} state a wrong value, and ${hl['wrong value: rule bound']} of these are the number from the rule itself, not a number from the report; only ${hl['wrong value: report distractor'] || 0} is a report distractor (the normal). So the direct answer fails mostly at the comparison and by anchoring on the rule, not on distractors. C4 gets ${ea.all.c4_fixes} of the ${ea.all.c1_errors} right (tolerant).</p>
<p><b>ALLaM 7B, C4 under strict scoring.</b> All ${hr.strict_errors} errors are on weather. In ${hr.json_cut} the extractor reply was cut off before the JSON closed: our prompt asked it to copy the source line word for word, and the report's fixed-width lines contain long runs of spaces. The value it had already written was right in ${hr.json_cut_value_right} of these ${hr.json_cut}. In ${hr.spec_slip} the model put the two bounds of a "between" rule as a list in the threshold field. ${hr.both} items had both problems. After the two repairs, ${hr.fixed_by_repairs} of ${hr.strict_errors} are right. The other ${hr.still_wrong} are wrong values: ${valueList}.</p>
<p><b>gpt-oss 20B.</b> With one report, all ${eg1.all.c1_errors} C1 errors are abstentions, and C4 gets all ${eg1.all.c4_fixes} of these right. But C4 makes ${(gvf1['no value'] || 0) + (gvf1.record || 0)} errors of its own: in ${gvf1['no value'] || 0} the extractor returned no value, and in ${gvf1.record || 0} it took the record high, which sits next to the observed value in the report. On items with a flipping distractor C4 gets ${pct(gFlip.C4_spec_code)} against ${pct(gFlip.C1_direct)} for C1. With both reports, C1 abstains on ${eg2.c1_abstain} items, 2 of them on the only dev day where the preliminary and final reports disagree (NYC low, 58 against 54), and C4's ${gvf2.record || 0} errors are all the record high. For a strong model, the extra extraction step adds errors about as often as it removes them.</p>
<p><b>Revisions.</b> The two reports differ on only ${rev.dev.differs} of ${rev.dev.n} dev weather items and change the outcome on ${rev.dev.flips} (${rev.test.differs} and ${rev.test.flips} of ${rev.test.n} on test). Real revisions are much rarer than in the edited set we planned in Milestone 2.</p>

<h2>8. Changes attempted and their effects</h2>
<ul>
<li><b>Spec format.</b> In our first version, one-sided rules could put the threshold in "low" or "high", and C4 got ${PL.C4_spec_code.correct} of ${PL.C4_spec_code.n} pilot items right. With a single "threshold" field it got ${PL.C4_v2_same_items.correct} of ${PL.C4_v2_same_items.n}. Tolerant scoring of the old outputs also gives ${PL.C4_v1_tolerant} of ${PL.C4_spec_code.n}.</li>
<li><b>B1 and output limit.</b> B1 abstained on ${PL.B1_no_evidence.abstain} of ${PL.B1_no_evidence.n} pilot items, so we now force YES or NO. ALLaM 7B was cut off at 60 tokens; at 320, strict invalid C1 answers are ${ea.c1_invalid_strict} of ${ea.c1_n}.</li>
<li><b>Parser fix.</b> Our parser for the report numbers missed times like "11:12 AM" and read only 144 of 384 reports. After the fix it reads all 384, and the dev items with a flipping distractor went from 15 to ${D.dev_dflip}.</li>
</ul>

<h2>9. Remaining gaps relative to our success criteria</h2>
<p>Our Milestone 2 metric was C4 minus C2 on edited contracts, which we dropped. The new main result is C4 minus C1 and C4 minus C2 under strict scoring, by model and item type, on the test set, which we have not run. Strict C4 is not yet a fair test of execution, because its two format problems are in our pipeline, not in the idea. Qwen 27B is at the ceiling on dev. We still need C2 and oracle runs for the larger models, C2-SC, B2 and the spec-agreement measure (H3). Finance and economics evidence is one line, so it tests reading the rule but not finding the value.</p>

<h2>10. Plan for the final two weeks</h2>
<ol>
<li><b>Nov 20 to 24 (Abhinav):</b> fix the two format problems inside the pipeline (a short quote, a schema check with one retry, JSON mode), re-check on dev and freeze the prompts. Then strict C4 is a fair test.</li>
<li><b>Nov 21 to 25 (Devansh):</b> run the test set (${D.by_split.test} items) with C1, C2 and C4 on all three models on a paid Groq tier, rerun the failed Qwen item, and finish B1 and the dev runs. Add real source text for finance and economics (BLS CPI release, AAA gas prices).</li>
<li><b>Nov 24 to 28 (Pranjal):</b> C2-SC at matched tokens, a logistic regression of when C4 helps (clustered by event), a router chosen on dev and scored on test (same items for every method, ties broken by mean tokens per item), and gpt-oss 120B.</li>
<li><b>Nov 28 to Dec 1 (all):</b> hand-label 30 errors per method and model by stage and cause.</li>
<li><b>Dec 1 to 3 (all):</b> demo and final report.</li>
</ol>
</body></html>`;

const outHtml = path.join(__dirname, 'm3_report.html');
const outPdf = path.join(__dirname, 'Milestone3_Progress_Report.pdf');
fs.writeFileSync(outHtml, html);
execFileSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new', '--disable-gpu', '--no-pdf-header-footer', `--print-to-pdf=${outPdf}`, pathToFileURL(outHtml).href],
  { stdio: 'ignore' });
console.log('wrote', outPdf);
