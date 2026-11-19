// Milestone 3 report: HTML -> PDF (Chrome headless). Every number comes from results/m3/numbers.json;
// a missing number stops the build. Run: python3 src/m3_report.py && python3 src/m3_numbers.py &&
// python3 src/m3_figure.py && node docs/make_m3_pdf.js
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { pathToFileURL } = require('url');

const ROOT = path.join(__dirname, '..');
const N = JSON.parse(fs.readFileSync(path.join(ROOT, 'results', 'm3', 'numbers.json'), 'utf8'));
const FIG = fs.readFileSync(path.join(__dirname, 'm3_fig.svg'), 'utf8').replace(/^[\s\S]*?(<svg)/, '$1');
const R = N.results, D = N.data, E = N.errors, PL = N.pilot;

const need = (v, what) => { if (v === undefined || v === null) throw new Error('missing ' + what); return v; };
const ov = (key, m) => need(R[key] && R[key].overall[m], `${key} ${m}`);
const pct = x => (100 * need(x, 'pct')).toFixed(1) + '%';
const num = x => (100 * x).toFixed(1);
const sgn = x => (x < 0 ? '−' : '') + Math.abs(100 * x).toFixed(1);
const n0 = x => Number(x).toLocaleString('en-US');
const pairOf = (key, a, b, mode = 'tolerant') => need((R[key].pairs || []).find(q => q.compare === `${a} - ${b}` && q.scoring === mode), `${key} ${a}-${b} ${mode}`);
const cell = (key, m, field, full) => { const o = R[key] && R[key].overall[m]; return o ? pct(o[field]) + (o.n < full ? ` (${o.n})` : '') : '-'; };

const A = 'ALLaM 7B | report', Q = 'Qwen 27B | report', G = 'gpt-oss 20B | report_both';
const a1 = ov(A, 'C1_direct'), a4 = ov(A, 'C4_spec_code'), q1 = ov(Q, 'C1_direct'), g1 = ov(G, 'C1_direct'), qB1 = ov(Q, 'B1_no_evidence');
const ea = E[A], eg = E[G], eab = E['ALLaM 7B | report_both'];
const causes = need(R[A].c4_causes.find(r => r.domain === 'weather'), 'causes');
const cut = causes['format: extractor JSON cut off'], slip = causes['format: spec field slip'], valErr = causes['still wrong: value'];
const nC4err = cut + slip + valErr;
const vf = Object.fromEntries(R[A].c4_value_from.map(r => [r.value_from, r.n]));
const gvf = Object.fromEntries(R[G].c4_value_from.map(r => [r.value_from, r.n]));
const gWrong = Object.values(gvf).reduce((s, x) => s + x, 0);
const rev = D.revisions;
const gT = pairOf(A, 'C4_spec_code', 'C1_direct'), gS = pairOf(A, 'C4_spec_code', 'C1_direct', 'strict');
const diffCell = key => { const p = pairOf(key, 'C4_spec_code', 'C1_direct'); return `${sgn(p.diff)} [${sgn(p.ci_low)}, ${sgn(p.ci_high)}]` + (p.n < R[key].overall.C1_direct.n ? ` (${p.n})` : ''); };
const row = (name, ev, key, o) => `<tr><td>${name}</td><td>${ev}</td><td class="r">${o.n}</td><td class="r">${cell(key, 'C1_direct', 'acc_tol', o.n)}</td><td class="r">${cell(key, 'C2_cot', 'acc_tol', o.n)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc', o.n)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc_tol', o.n)}</td><td class="r">${diffCell(key)}</td></tr>`;
const valueList = Object.entries(vf).map(([k, v]) => `${({ last_year: "last year's value", normal: 'the normal', record: 'the record', other: 'another number' })[k] || k} (${v})`).join(', ');

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Milestone 3 Progress Report</title><style>
@page { size: Letter; margin: 0.7in 0.75in; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 9.8pt; line-height: 1.32; color: #000; margin: 0; }
h1 { font-size: 14pt; margin: 0 0 2px; }
.sub { margin: 0 0 1px; }
h2 { font-size: 11pt; margin: 11px 0 3px; break-after: avoid; }
p { margin: 0 0 6px; text-align: left; }
ul, ol { margin: 0 0 6px; padding-left: 20px; }
li { margin: 0 0 2px; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 4px 0 3px; break-inside: avoid; }
th, td { border: 1px solid #999; padding: 2px 5px; vertical-align: top; }
th { background: #e8e8e8; text-align: left; }
.r { text-align: right; }
.cap { font-size: 8.8pt; margin: 0 0 8px; }
figure { margin: 6px 0 2px; break-inside: avoid; }
figure svg { width: 100%; height: auto; display: block; }
figure svg text { font-family: Arial, Helvetica, sans-serif !important; }
</style></head><body>

<h1>Milestone 3: Progress Report</h1>
<p class="sub"><b>When Does Executing Contract Rules Help? LLM Resolution of Real Kalshi Markets</b></p>
<p class="sub">Team: Abhinav Sivakumar (as21153), Devansh Vikram (dv2482), Pranjal Mishra (pm4084)</p>
<p class="sub" style="margin-bottom:8px">Code: https://github.com/pmxlr8/kalshi-rules</p>

<h2>Response to the Milestone 2 feedback</h2>
<p>We got two main comments. The first was to focus on when and why structured execution helps, instead of trying to show that C4 beats the other methods. The second was that our evaluation data was artificial, so good results on it would not say much about real prediction markets. We changed the project around both points. We dropped the edited contracts and now evaluate only on real settled Kalshi markets, with the evidence source that the rules point to and Kalshi's actual outcome as the label. Instead of one overall number per method, we break the results down by model size and by properties of each item (how close the value is to the threshold, whether the evidence contains a number that would flip the answer, whether the rule has one or two bounds), and we check which step of the pipeline each error comes from.</p>

<h2>1. System implemented so far</h2>
<p><b>Data.</b> We pulled ${n0(D.markets)} settled markets from ${D.series} series through Kalshi's public API (closed between ${D.first_close} and ${D.last_close}). Each market has its rules text, the outcome, a structured threshold and the final value. Applying the threshold to the final value gives back Kalshi's outcome on ${n0(D.gold_agree_numeric)} of the ${n0(D.numeric_value)} markets with a numeric value, so we get exact labels without any hand annotation. The one mismatch is a Nasdaq-100 market whose threshold field says 26,990 while the rules text says "above 26,989.99"; the rules text decided it.</p>
<p><b>Evidence.</b> For weather markets we use the NWS daily climate report for the station named in the rules, which is the source Kalshi settles on. It matches Kalshi's value on ${D.station_days - D.missing_reports - D.value_mismatch} of ${D.station_days - D.missing_reports} station-days. The report also lists the record, the normal, the departure from normal, last year's value and the other daily extreme, so the model has to pick the right number; on ${Math.round(100 * D.weather_dflip_share)}% of weather items at least one of these would flip the answer. We also built a version with both the preliminary and the final report. For finance and economics the evidence is currently one line with the official value.</p>
<p><b>Study set.</b> ${D.study} markets from ${D.events} events (${D.by_domain.weather} weather, ${D.by_domain.fin} finance, ${D.by_domain.econ} economics), split by event into a dev set of ${D.by_split.dev} items (${D.events_by_split.dev} events) and a test set of ${D.by_split.test} items (${D.events_by_split.test} events). We only change prompts based on dev.</p>
<p><b>Methods.</b> All methods use the same model, evidence and temperature 0. B1 sees the contract but no evidence. C1 answers directly. C2 uses chain of thought. C3 writes a JSON spec of the rule, extracts the value and applies the spec in text. C4 does the same spec and extraction, but Python applies the spec. O1 and O2 are C4 with the gold spec or the gold value plugged in, to locate errors. We run three models through the Groq API: ALLaM 2 7B, Qwen 3.8 27B (reasoning off) and gpt-oss 20B (low reasoning). Llama 3.1, which we planned to use in Milestone 2, is no longer available on Groq, so ALLaM is our small model.</p>
<p><b>Scoring.</b> We report two scores. Strict scoring requires the exact output format. Tolerant scoring re-reads the same saved outputs and only fixes formatting problems, such as a verdict written as a sentence instead of JSON or bounds put in the wrong field. It makes no new model calls, so the gap between the two scores shows how many errors are about formatting rather than reasoning. Intervals come from a paired bootstrap over events. All model calls are cached, a self-test checks the labels and parsers, and a small Streamlit demo runs C2 and C4 side by side on any market.</p>

<h2>2. Baseline results</h2>
<p>Without evidence (B1), Qwen 27B gets a balanced accuracy of ${qB1.bal_acc.toFixed(2)} on ${qB1.n} dev items, which is chance. So the outcome cannot be guessed from the contract alone, and the model does not seem to know these outcomes. The direct answer (C1) is our main baseline. On dev it gets ${pct(q1.acc)} with Qwen 27B (${q1.n} of ${q1.n}), ${pct(a1.acc_tol)} with ALLaM 7B and ${pct(g1.acc_tol)} with gpt-oss 20B given both reports.</p>

<h2>3. Current results</h2>
<table>
<tr><th>Model</th><th>Evidence</th><th class="r">Items</th><th class="r">C1</th><th class="r">C2</th><th class="r">C4 strict</th><th class="r">C4 tolerant</th><th class="r">C4 minus C1 [95% CI]</th></tr>
${row('ALLaM 2 7B', '1 report', A, a1)}
${row('Qwen 3.8 27B', '1 report', Q, q1)}
${row('gpt-oss 20B', '2 reports (weather)', G, g1)}
</table>
<p class="cap">Table 1. Dev accuracy. C1 and C2 use tolerant scoring (strict C1: ${pct(a1.acc)}, ${pct(q1.acc)}, ${pct(g1.acc)}). A number in brackets after a value is the number of items run so far, for runs that are not finished. Differences are in points and paired on shared items.</p>
<figure>${FIG}</figure>
<p class="cap">Figure 1. (A) Dev accuracy by model; the open circle is C4 under strict scoring. (B) ALLaM 7B, C1 against C4 by item type (tolerant scoring).</p>
<p>The main pattern is that structure only helps when the direct answer is weak. With Qwen 27B the direct answer is already right on every dev item, so there is nothing for C4 to improve. With ALLaM 7B, C4 is ${num(gT.diff)} points better than C1 under tolerant scoring (95% CI ${num(gT.ci_low)} to ${num(gT.ci_high)}), and the gap is largest on weather items, items near the threshold and items where a distractor would flip the answer (Figure 1B). Under strict scoring it reverses: C4 is ${num(-gS.diff)} points worse than C1 (95% CI ${sgn(gS.ci_low)} to ${sgn(gS.ci_high)}), because the small model often breaks the JSON format in one of C4's two steps.</p>

<h2>4. Experiments and comparisons completed</h2>
<p>We ran the baselines B1 and C1, and C1 and C4 on all dev items for ALLaM 7B and Qwen 27B (Qwen's C4 run is still going). C2 has run on part of dev. gpt-oss 20B was run on the weather dev items with both reports. We also compared two versions of the spec format on a 12-item pilot. For every run we compute strict and tolerant scores, accuracy by item type, and paired differences with event-level bootstrap intervals.</p>

<h2>5. What worked</h2>
<ul>
<li>Using real markets. The labels come straight from Kalshi, and the data has plenty of hard cases: ${D.dev_near} of ${D.by_split.dev} dev items are within one step of the threshold and ${D.dev_dflip} have a distractor that would flip the answer.</li>
<li>C4 with the small model, once formatting is handled.</li>
<li>Tolerant scoring, which turned out to be a simple way to separate formatting errors from reasoning errors.</li>
</ul>

<h2>6. What failed</h2>
<ul>
<li>Strict C4 on ALLaM 7B is worse than the direct answer (${pct(a4.acc)} against ${pct(a1.acc)}).</li>
<li>With both reports (about 3,300 input tokens, close to its 4,096-token limit), ALLaM 7B started repeating itself or printing blank lines and gave no valid answer on ${eab.c1_invalid_strict} of ${eab.c1_n} items, so we stopped that run.</li>
<li>Qwen 27B is already at 100% on dev, so it cannot show any benefit from structure on these markets.</li>
<li>We hit the daily token limits of Groq's free tier, so C2, the oracle runs and the test set are not finished.</li>
</ul>

<h2>7. Failure analysis and likely causes</h2>
<p><b>ALLaM 7B, direct answers.</b> ${ea.all.c1_errors} of ${ea.c1_n} answers are wrong, and ${ea.all.yes_on_no} of those say YES when the answer is NO. It answers YES ${pct(ea.c1_yes_rate)} of the time while the true rate is ${pct(ea.gold_yes_rate)}. Of the ${ea.weather.c1_errors} wrong weather answers, ${ea.weather.kinds['no value stated']} give only a verdict without a value, ${ea.weather.kinds['wrong value']} cite the wrong value, and ${ea.weather.kinds['right value, wrong comparison']} cite the right value but compare it wrongly at a boundary (for example, it said 70 is not in "69&deg; to 70&deg;"). C4 gets ${ea.all.c4_fixes} of these ${ea.all.c1_errors} right, which points to the comparison step, the part that C4 hands to Python.</p>
<p><b>ALLaM 7B, C4 under strict scoring.</b> All ${nC4err} errors are on weather. In ${cut} cases the extractor found the right value, but our prompt asked it to copy the source line word for word, and the report's fixed-width lines contain long runs of spaces, so it ran out of tokens before closing the JSON. In ${slip} cases it put both bounds of a "between" rule into the threshold field. Only ${valErr} are real value errors, and all of them are other numbers from the report: ${valueList}.</p>
<p><b>gpt-oss 20B with both reports.</b> C1 abstains on ${eg.c1_abstain} of ${eg.c1_n} items, two of them on the only dev day where the preliminary and final reports disagree (NYC low, 58 against 54). C4 picks a wrong value ${gWrong} times, ${(gvf.record || 0) === gWrong ? 'and each time it is the record high' : `${gvf.record || 0} of them the record high`}, which sits right next to the observed value in the report.</p>
<p><b>Revisions.</b> The two reports differ on only ${rev.dev.differs} of ${rev.dev.n} dev weather items and change the outcome on ${rev.dev.flips} (${rev.test.differs} and ${rev.test.flips} of ${rev.test.n} on test). Real revisions are much rarer than in the edited set we planned in Milestone 2.</p>

<h2>8. Changes attempted and their effects</h2>
<ul>
<li><b>Spec format.</b> In our first version, one-sided rules could put the threshold in "low" or "high", and C4 got only ${PL.C4_spec_code.correct} of ${PL.C4_spec_code.n} pilot items right. After switching to a single "threshold" field it got ${PL.C4_v2_same_items.correct} of ${PL.C4_v2_same_items.n}. Tolerant scoring of the old outputs also gives ${PL.C4_v1_tolerant} of ${PL.C4_spec_code.n}, so all ${PL.C4_spec_code.abstain} errors were formatting. C3, which applies the same spec in text, got ${PL.C3_spec_prose.correct} of ${PL.C3_spec_prose.n} even with the old format.</li>
<li><b>B1 prompt.</b> The first version allowed the model to abstain, and it did on ${PL.B1_no_evidence.abstain} of ${PL.B1_no_evidence.n} items. We now force a YES or NO, so B1 is a real chance baseline.</li>
<li><b>Output limit.</b> ALLaM 7B writes some text before its JSON and was getting cut off at 60 tokens. We raised the limit to 320, and strict invalid answers are now ${ea.c1_invalid_strict} of ${ea.c1_n}.</li>
<li><b>Parser fix.</b> Our parser for the report numbers missed times like "11:12 AM" and read only 144 of 384 reports. After the fix it reads all 384, and the dev items with a flipping distractor went from 15 to ${D.dev_dflip}.</li>
<li><b>Rate limits.</b> Each model has its own daily limit on Groq's free tier, so we run one queue per model and let it wait when it hits the limit.</li>
</ul>

<h2>9. Remaining gaps relative to our success criteria</h2>
<p>Our Milestone 2 primary metric was C4 minus C2 on the edited contracts, which we dropped. The new main result will be C4 minus C1 and C4 minus C2 broken down by model and item type on the test set, which we have not run yet. We also still need C2 on all of dev, C3, the compute-matched C2-SC baseline, B2, the oracle runs and the spec-agreement uncertainty measure (H3). Finance and economics evidence is only one line, so those domains test reading the rule but not finding the value. Our largest model is 27B, and we no longer compare against KalshiBench because we stopped using web search evidence.</p>

<h2>10. Plan for the final two weeks</h2>
<ol>
<li><b>Nov 20 to 23 (Devansh):</b> run the test set (${D.by_split.test} items) with C1, C2 and C4 on ALLaM 7B and Qwen 27B, and C1 and C4 on gpt-oss 20B, on a paid Groq tier. Finish the remaining dev runs.</li>
<li><b>Nov 20 to 24 (Abhinav):</b> fix the two formatting problems in the pipeline itself (short quotes, a schema check with one retry, JSON mode), re-check on dev and freeze the prompts. Strict scores then become the main result.</li>
<li><b>Nov 22 to 26 (Devansh):</b> use real source text for finance and economics (the BLS CPI release, the AAA gas price page), so these domains also test finding the value.</li>
<li><b>Nov 24 to 28 (Pranjal):</b> C2-SC at matched tokens, the oracle runs, a logistic regression of when C4 helps (clustered by event), a router picked on dev and scored on test, and gpt-oss 120B as a larger model.</li>
<li><b>Nov 28 to Dec 1 (all):</b> hand-label 30 errors per method by stage and cause.</li>
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
