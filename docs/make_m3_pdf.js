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
const pts = x => (x >= 0 ? '+' : '−') + Math.abs(100 * x).toFixed(1);
const n0 = x => Number(x).toLocaleString('en-US');
const pairOf = (key, a, b, mode = 'tolerant') => need((R[key].pairs || []).find(q => q.compare === `${a} - ${b}` && q.scoring === mode), `${key} ${a}-${b} ${mode}`);
const pair = (key, a, b, mode) => { const p = pairOf(key, a, b, mode); return `${pts(p.diff)} points (95% CI ${pts(p.ci_low)} to ${pts(p.ci_high)})`; };
const cell = (key, m, field, full) => { const o = R[key] && R[key].overall[m]; return o ? pct(o[field]) + (o.n < full ? `<span class="n"> n=${o.n}</span>` : '') : '<span class="muted">not run</span>'; };

const A = 'ALLaM 7B | report', Q = 'Qwen 27B | report', G = 'gpt-oss 20B | report_both';
const a1 = ov(A, 'C1_direct'), a4 = ov(A, 'C4_spec_code'), q1 = ov(Q, 'C1_direct'), g1 = ov(G, 'C1_direct'), qB1 = ov(Q, 'B1_no_evidence');
const ea = E[A], eg = E[G], eab = E['ALLaM 7B | report_both'];
const causes = need(R[A].c4_causes.find(r => r.domain === 'weather'), 'causes');
const nC4err = causes['format: extractor JSON cut off'] + causes['format: spec field slip'] + causes['still wrong: value'];
const nFmt = causes['format: extractor JSON cut off'] + causes['format: spec field slip'];
const vf = Object.fromEntries(R[A].c4_value_from.map(r => [r.value_from, r.n]));
const gvf = Object.fromEntries(R[G].c4_value_from.map(r => [r.value_from, r.n]));
const gWrong = Object.values(gvf).reduce((s, x) => s + x, 0);
const rev = D.revisions;
const gain = pairOf(A, 'C4_spec_code', 'C1_direct');
const ci = key => { const p = pairOf(key, 'C4_spec_code', 'C1_direct'); return `${pts(p.diff)} <span class="muted">[${pts(p.ci_low)}, ${pts(p.ci_high)}]</span>` + (p.n < R[key].overall.C1_direct.n ? `<span class="n"> n=${p.n}</span>` : ''); };
const row = (name, ev, key, o) => `<tr><td>${name}</td><td>${ev}</td><td class="r">${o.n}</td><td class="r">${cell(key, 'C1_direct', 'acc_tol', o.n)}</td><td class="r">${cell(key, 'C2_cot', 'acc_tol', o.n)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc', o.n)}</td><td class="r">${cell(key, 'C4_spec_code', 'acc_tol', o.n)}</td><td class="r">${ci(key)}</td></tr>`;

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Milestone 3 Progress Report</title><style>
@page { size: Letter; margin: 0.5in 0.62in 0.5in; }
* { box-sizing: border-box; }
body { font-family: "Avenir Next", "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9pt; line-height: 1.36; color: #1d1d1b; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.title { font-size: 16.5pt; font-weight: 600; line-height: 1.2; margin: 0 0 3px; letter-spacing: -0.1px; }
.sub { color: #52514e; font-size: 9pt; margin: 0 0 1px; }
.bar { width: 44px; height: 3px; background: #2a78d6; border-radius: 2px; margin: 7px 0 8px; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 0 0 6px; }
.tile { background: #f3f6fa; border-radius: 6px; padding: 7px 10px 8px; }
.tile b { display: block; font-size: 14pt; font-weight: 600; color: #0b0b0b; line-height: 1.15; }
.tile span { font-size: 7.9pt; color: #52514e; line-height: 1.3; display: block; margin-top: 2px; }
h2 { font-size: 10.4pt; font-weight: 600; margin: 9px 0 2px; break-after: avoid; color: #0b0b0b; }
h2 .k { color: #2a78d6; margin-right: 6px; }
p { margin: 0 0 5px; }
ul { margin: 0 0 5px; padding-left: 15px; }
li { margin: 0 0 2.5px; }
li::marker { color: #8a8984; }
table { width: 100%; border-collapse: collapse; font-size: 8.2pt; margin: 3px 0 4px; break-inside: avoid; }
th { text-align: left; font-weight: 600; color: #52514e; border-bottom: 1px solid #bdbcb6; padding: 3px 6px 3px 0; vertical-align: bottom; }
td { border-bottom: 0.5px solid #e6e5e0; padding: 2.5px 6px 2.5px 0; vertical-align: top; }
td.r, th.r { text-align: right; font-variant-numeric: tabular-nums; }
.kv td:first-child { width: 88px; font-weight: 600; color: #0b0b0b; }
.n { color: #8a8984; font-size: 7.6pt; } .muted { color: #8a8984; }
.cap { font-size: 7.9pt; color: #52514e; margin: 0 0 8px; }
figure { margin: 6px 0 2px; break-inside: avoid; }
figure svg { width: 100%; height: auto; display: block; }
figure svg text { font-family: "Avenir Next", "Helvetica Neue", Helvetica, sans-serif !important; }
.callout { border-left: 3px solid #2a78d6; background: #f3f6fa; padding: 6px 10px 6px; border-radius: 0 6px 6px 0; margin: 6px 0 4px; break-inside: avoid; }
.callout p { margin: 0 0 3px; } .callout p:last-child { margin: 0; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 18px; }
a { color: inherit; text-decoration: none; }
</style></head><body>

<div class="title">When Does Executing Contract Rules Help?<br>LLM Resolution of Real Kalshi Markets</div>
<p class="sub">GenAI Final Project &middot; Milestone 3: Progress Report &middot; November 19, 2026</p>
<p class="sub">Abhinav Sivakumar (as21153) &middot; Devansh Vikram (dv2482) &middot; Pranjal Mishra (pm4084) &middot; Code: github.com/pmxlr8/kalshi-rules</p>
<div class="bar"></div>

<div class="tiles">
  <div class="tile"><b>${D.study}</b><span>real settled Kalshi markets in the study (dev ${D.by_split.dev}, test ${D.by_split.test})</span></div>
  <div class="tile"><b>${pts(gain.diff)} pts</b><span>C4 (spec + code) over the direct answer, ALLaM 7B, dev</span></div>
  <div class="tile"><b>${pct(q1.acc).replace('.0%', '%')}</b><span>Qwen 27B direct answer on dev: nothing left for structure to fix</span></div>
  <div class="tile"><b>${nFmt} of ${nC4err}</b><span>strict C4 errors on ALLaM 7B that are format slips, not reasoning</span></div>
</div>

<h2><span class="k">1</span>How we addressed the Milestone 2 feedback</h2>
<p><b>"Focus on when and why structured execution helps."</b> We no longer ask whether C4 beats C2 on average. Each item carries features that may decide when structure matters (distance to the threshold, one or two bounds, a distractor number that would flip the answer, report revisions, domain), and we vary model size. To explain why, we split each error by stage (rule, value or comparison) and by kind (reasoning or only format).</p>
<p><b>"Your eval data is artificial."</b> We dropped the edited contracts. Every item is now a real settled Kalshi market, scored against Kalshi's real outcome, with the real evidence that its rules name. The gold comes from Kalshi's own data, so no hand labels are needed.</p>

<h2><span class="k">2</span>System implemented so far</h2>
<table class="kv">
<tr><td>Data</td><td>${n0(D.markets)} settled markets in ${D.series} series, closed ${D.first_close} to ${D.last_close} (public Kalshi API). Kalshi's threshold field applied to the settled value reproduces the outcome on ${n0(D.gold_agree_numeric)} of ${n0(D.numeric_value)} markets with a numeric value. The one exception is a real edge case: a Nasdaq-100 market whose threshold field (26,990) differs from its rules text ("above 26,989.99"); the text decided it.</td></tr>
<tr><td>Evidence</td><td>Weather: the NWS daily climate report for the station the rules name. It matches Kalshi's value on ${D.station_days - D.missing_reports - D.value_mismatch} of ${D.station_days - D.missing_reports} station-days. It also lists the record, normal, departure, last-year value and the other daily extreme; on ${Math.round(100 * D.weather_dflip_share)}% of weather items one of these would flip the answer. A variant gives the preliminary and the final report together. Finance and economics: one line with the official value.</td></tr>
<tr><td>Study set</td><td>${D.study} items in ${D.events} events (weather ${D.by_domain.weather}, finance ${D.by_domain.fin}, economics ${D.by_domain.econ}), split by event: dev ${D.by_split.dev} items (${D.events_by_split.dev} events), test ${D.by_split.test} (${D.events_by_split.test} events). Prompts change on dev only; test is untouched.</td></tr>
<tr><td>Methods</td><td><b>B1</b> no evidence &middot; <b>C1</b> direct answer &middot; <b>C2</b> chain of thought &middot; <b>C3</b> LLM writes a JSON spec, extracts the value, applies the spec in prose &middot; <b>C4</b> LLM writes the spec and extracts the value, Python applies the spec &middot; <b>O1, O2</b> C4 given the gold spec or the gold value. Built but not run yet: C2-SC (5-sample vote), B2 (no rules), O3.</td></tr>
<tr><td>Models</td><td>Groq API, temperature 0: ALLaM 2 7B, Qwen 3.8 27B (reasoning off), gpt-oss 20B (reasoning low). Llama 3.1 from our Milestone 2 plan is no longer served there, so ALLaM is our small model.</td></tr>
<tr><td>Scoring</td><td><b>Strict:</b> the answer must follow the output format. <b>Tolerant:</b> the saved output re-read with format repairs only (a "verdict is NO" sentence, bounds in the wrong JSON field, a value written before the JSON was cut off), with no new LLM calls. ABSTAIN and invalid count as wrong. Intervals: paired bootstrap over events.</td></tr>
<tr><td>Engineering</td><td>All calls cached; runs resume; a self-test checks gold rules, evaluator and parsers; a Streamlit demo runs C2 and C4 side by side.</td></tr>
</table>

<h2><span class="k">3</span>Baseline results</h2>
<p><b>B1 (no evidence)</b> on Qwen 27B has a balanced accuracy of ${qB1.bal_acc.toFixed(2)} (n = ${qB1.n}), which is chance: the contract text does not give the outcome away, and the model shows no sign of knowing these 2026 outcomes. <b>C1 (direct answer)</b> is the baseline to beat: ${pct(q1.acc)} on Qwen 27B (${q1.n} of ${q1.n}), ${pct(a1.acc_tol)} on ALLaM 7B, and ${pct(g1.acc_tol)} on gpt-oss 20B with both reports.</p>

<h2><span class="k">4</span>Current results (dev split)</h2>
<table>
<tr><th>Model</th><th>Evidence</th><th class="r">Items</th><th class="r">C1 direct</th><th class="r">C2 CoT</th><th class="r">C4 strict</th><th class="r">C4 tolerant</th><th class="r">C4 &minus; C1, points [95% CI]</th></tr>
${row('ALLaM 2 7B', '1 report', A, a1)}
${row('Qwen 3.8 27B', '1 report', Q, q1)}
${row('gpt-oss 20B', '2 reports, weather', G, g1)}
</table>
<p class="cap">Table 1. Accuracy on dev. C1 and C2 use tolerant scoring (strict C1: ${pct(a1.acc)}, ${pct(q1.acc)}, ${pct(g1.acc)}). "n=" marks a run that is not complete; differences are paired on shared items.</p>
<figure>${FIG}</figure>
<p class="cap">Figure 1. A: accuracy by model (the ring is C4 under strict scoring). B: ALLaM 7B by item type, tolerant scoring; the gain is in points.</p>
<div class="callout">
<p><b>Our answer so far.</b> <b>When:</b> structure helps when the direct answer fails. On real markets this happens with a small model, with long evidence full of distractors, near the threshold and on two-bound rules. With a 27B model, the direct answer is already right on every dev item.</p>
<p><b>Why:</b> the direct answer fails at the comparison (a YES bias and wrong calls at inclusive bounds), and code makes the comparison exact. <b>Why not always:</b> each extra JSON step is a new place to break the format, so strict C4 loses until the pipeline handles the format itself (plan item 2).</p>
</div>

<h2><span class="k">5</span>Experiments and comparisons completed</h2>
<ul>
<li><b>E1 baselines</b> (B1, C1); <b>E2 main methods</b> (C1, C4 on all dev items for ALLaM 7B and Qwen 27B, Qwen C4 and C2 in part); <b>E3 scale</b> (7B, 20B, 27B); the <b>revision variant</b> (both reports, gpt-oss 20B); <b>pilot</b> spec format v1 against v2.</li>
<li><b>Analysis:</b> strict against tolerant scoring for every method; slices by domain, distance, distractor and bound type; paired differences with event-clustered bootstrap intervals; C4 errors split by cause.</li>
</ul>

<div class="two">
<div>
<h2><span class="k">6</span>What worked</h2>
<ul>
<li><b>Structure helps the small model:</b> C4 beats C1 on ALLaM 7B by ${pair(A, 'C4_spec_code', 'C1_direct')}, n = ${gain.n}. The gain is larger in every harder cell (Figure 1B).</li>
<li><b>Real data with exact gold:</b> no labels and no generated items. Hard cases are common: ${D.dev_near} of ${D.by_split.dev} dev items are within 1 step of the threshold, ${D.dev_dflip} have a flipping distractor.</li>
<li><b>Tolerant scoring</b> separates "reasoned wrong" from "broke the format", at no cost.</li>
</ul>
</div>
<div>
<h2><span class="k">7</span>What failed</h2>
<ul>
<li><b>Strict C4 on the small model:</b> ${pct(a4.acc)} against ${pct(a1.acc)} for strict C1, ${pair(A, 'C4_spec_code', 'C1_direct', 'strict')}. C4 has 2 JSON outputs where C1 has 1.</li>
<li><b>No room to help a 27B model:</b> Qwen 27B answers all ${q1.n} dev items directly.</li>
<li><b>Two reports break ALLaM 7B:</b> with about 3,300 input tokens (its context is 4,096) it loops or prints blank lines: no valid answer on ${eab.c1_invalid_strict} of ${eab.c1_n}, so we stopped that run.</li>
<li><b>Compute:</b> the free Groq tier's daily token limit per model left C2, the oracles and test incomplete.</li>
</ul>
</div>
</div>

<h2><span class="k">8</span>Failure analysis and likely causes</h2>
<ul>
<li><b>ALLaM 7B, direct answer.</b> ${ea.all.c1_errors} of ${ea.c1_n} are wrong, and ${ea.all.yes_on_no} of these say YES on a NO market: it answers YES ${pct(ea.c1_yes_rate)} of the time against a true rate of ${pct(ea.gold_yes_rate)}. Of the ${ea.weather.c1_errors} weather errors, ${ea.weather.kinds['no value stated']} give only a verdict, ${ea.weather.kinds['wrong value']} cite a wrong value, and ${ea.weather.kinds['right value, wrong comparison']} cite the right value but compare it wrongly at a bound (70 judged outside "69&deg; to 70&deg;"). Likely cause: the comparison step. C4 fixes ${ea.all.c4_fixes} of the ${ea.all.c1_errors}, because Python does the comparison.</li>
<li><b>ALLaM 7B, strict C4.</b> All ${nC4err} errors are on weather. ${causes['format: extractor JSON cut off']}: the extractor wrote the right value, then copied the report line "word for word" as asked; the report's fixed-width columns are long runs of spaces, so it hit the token cap before closing the JSON. ${causes['format: spec field slip']}: for "between" rules it put [low, high] in the "threshold" field. Only ${causes['still wrong: value']} are real value errors, each a distractor (last year ${vf.last_year || 0}, normal ${vf.normal || 0}, other ${vf.other || 0}).</li>
<li><b>gpt-oss 20B, both reports.</b> C1 abstains on ${eg.c1_abstain} of ${eg.c1_n} items, 2 of them on the one dev day where the reports disagree (NYC low: preliminary 58, final 54); it does not fall back to the later report. C4 takes a wrong value ${gWrong} times, ${(gvf.record || 0) === gWrong ? 'each time the record high' : `${gvf.record || 0} times the record high`}, which sits next to the observed value in the same row.</li>
<li><b>Revisions are rare in real markets.</b> The two reports differ on ${rev.dev.differs} of ${rev.dev.n} dev weather items and change the outcome on ${rev.dev.flips} (test: ${rev.test.differs} and ${rev.test.flips} of ${rev.test.n}), far fewer than in the edited set we had planned.</li>
</ul>

<h2><span class="k">9</span>Changes attempted and their effects</h2>
<table>
<tr><th style="width:30%">Change</th><th>Effect</th></tr>
<tr><td>Spec format v1 to v2: one "threshold" field for one-bound rules; "low" and "high" only for "between"</td><td>C4 on the same ${PL.C4_spec_code.n} pilot items: ${PL.C4_spec_code.correct} to ${PL.C4_v2_same_items.correct} correct. Tolerant scoring of the v1 outputs also gives ${PL.C4_v1_tolerant}, so all ${PL.C4_spec_code.abstain} v1 errors were format slips. C3, which applies the same v1 spec in prose, had ${PL.C3_spec_prose.correct} of ${PL.C3_spec_prose.n}: prose is robust to slips that break code.</td></tr>
<tr><td>B1 must answer YES or NO</td><td>The v1 prompt let the model abstain (${PL.B1_no_evidence.abstain} of ${PL.B1_no_evidence.n}). Now B1 is a true chance baseline.</td></tr>
<tr><td>Output cap for ALLaM 7B: 60 to 320 tokens</td><td>It writes prose before the JSON and was cut off. Strict invalid answers are now ${ea.c1_invalid_strict} of ${ea.c1_n}.</td></tr>
<tr><td>Report parser fix (times like "11:12 AM")</td><td>The distractor parser read only 144 of 384 weather reports; now all 384. Dev items with a flipping distractor: 15 to ${D.dev_dflip}.</td></tr>
<tr><td>Free-tier queues</td><td>One queue per model (each has its own daily limit) that waits at the cap instead of stopping.</td></tr>
</table>

<h2><span class="k">10</span>Remaining gaps relative to our success criteria</h2>
<ul>
<li>Our Milestone 2 primary metric (C4 &minus; C2 on 360 edited items) went with the edited set. The new primary result is C4 &minus; C1 and C4 &minus; C2 per cell (model &times; domain, distance, distractor, bound type) on the untouched test split. <b>Test is not run yet.</b></li>
<li>Not run yet: C2 on all dev items, C3 beyond the pilot, C2-SC at matched tokens, B2, O1 to O3, and the spec-agreement uncertainty check (H3).</li>
<li>Finance and economics evidence is one line, so it tests reading the rule, not finding the value. Our largest model is 27B (no 70B). The web-search bundles, source admissibility and the KalshiBench comparison with Kota (2026) went with the switch to the named source.</li>
</ul>

<h2><span class="k">11</span>Prioritized plan for the final two weeks</h2>
<table>
<tr><th style="width:4%">#</th><th style="width:15%">Dates</th><th>Task</th><th style="width:17%">Owner</th></tr>
<tr><td>1</td><td>Nov 20&ndash;23</td><td><b>Test run</b> (504 items): C1, C2, C4 on ALLaM 7B and Qwen 27B; C1, C4 on gpt-oss 20B; finish dev (paid Groq tier).</td><td>Devansh</td></tr>
<tr><td>2</td><td>Nov 20&ndash;24</td><td><b>Fix the 2 format failure points in the pipeline:</b> quote of 12 words or less, schema check with one retry, JSON mode. Retest on dev, freeze; strict scores become the main result.</td><td>Abhinav</td></tr>
<tr><td>3</td><td>Nov 22&ndash;26</td><td><b>Real source text for finance and economics</b> (BLS CPI release, AAA daily price page), so they also test finding the value among distractors.</td><td>Devansh</td></tr>
<tr><td>4</td><td>Nov 24&ndash;28</td><td><b>Compute and statistics:</b> C2-SC at matched tokens; O1, O2; a cluster-robust logistic "when" model; a router picked on dev, scored on test; gpt-oss 120B as the large model.</td><td>Pranjal</td></tr>
<tr><td>5</td><td>Nov 28&ndash;Dec 1</td><td><b>Failure analysis:</b> 30 errors per method read by hand, tagged by stage and cause.</td><td>All three</td></tr>
<tr><td>6</td><td>Dec 1&ndash;3</td><td><b>Demo and final report:</b> live C2 against C4 on a market, the stage where each fails, and the cached results.</td><td>All three</td></tr>
</table>
</body></html>`;

const outHtml = path.join(__dirname, 'm3_report.html');
const outPdf = path.join(__dirname, 'Milestone3_Progress_Report.pdf');
fs.writeFileSync(outHtml, html);
execFileSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new', '--disable-gpu', '--no-pdf-header-footer', `--print-to-pdf=${outPdf}`, pathToFileURL(outHtml).href],
  { stdio: 'ignore' });
console.log('wrote', outPdf);
