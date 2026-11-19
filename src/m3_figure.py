"""Figure 1 of the Milestone 3 report, from results/m3/numbers.json. Writes docs/m3_fig.svg and .png."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import ROOT

C1, C4, INK, INK2, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                     "svg.fonttype": "none", "font.size": 8.5, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK})

N = json.loads((ROOT / "results" / "m3" / "numbers.json").read_text())
R = N["results"]

def style(ax):
    ax.set_xlim(0, 104); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(axis="y", length=0); ax.tick_params(axis="x", length=0)

fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.95})

# Panel A: accuracy by model
rows = [("ALLaM 7B", "ALLaM 7B | report"), ("Qwen 27B", "Qwen 27B | report"), ("gpt-oss 20B\n(2 reports)", "gpt-oss 20B | report_both")]
for y, (name, key) in enumerate(rows[::-1]):
    o = R[key]["overall"]
    c1, c4s, c4t = 100 * o["C1_direct"]["acc_tol"], 100 * o["C4_spec_code"]["acc"], 100 * o["C4_spec_code"]["acc_tol"]
    a.plot([min(c1, c4s, c4t), max(c1, c4s, c4t)], [y, y], color=GRID, lw=2, zorder=1, solid_capstyle="round")
    a.scatter([c4s], [y], s=46, facecolor="white", edgecolor=C4, lw=1.8, zorder=3)
    a.scatter([c1], [y], s=46, color=C1, edgecolor="white", lw=1.2, zorder=4)
    a.scatter([c4t], [y], s=46, color=C4, edgecolor="white", lw=1.2, zorder=5)
    a.text(108, y, f"{c1:.0f} / {c4t:.0f}", va="center", ha="left", fontsize=7.8, color=INK2)
a.text(108, len(rows) - 0.55, "C1 / C4", va="center", ha="left", fontsize=7.8, color=INK2)
a.set_yticks(range(len(rows))); a.set_yticklabels([r[0] for r in rows[::-1]]); a.set_ylim(-0.6, len(rows) - 0.4)
style(a); a.set_title("(A) Accuracy by model", loc="left", fontsize=9, pad=8)
a.scatter([], [], s=40, color=C1, label="C1 direct"); a.scatter([], [], s=40, color=C4, label="C4 spec + code")
a.scatter([], [], s=40, facecolor="white", edgecolor=C4, lw=1.6, label="C4 strict scoring")
fig.legend(*a.get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.07), ncol=3, frameon=False, fontsize=8, handletextpad=0.2, columnspacing=1.6)

# Panel B: ALLaM 7B by item feature (tolerant)
S = R["ALLaM 7B | report"]["slices"]
def get(col, val):
    return next(r for r in S[col] if str(r[col]).lower() == str(val).lower())
feats = [("Weather report", "domain", "weather"), ("Finance, 1 line", "domain", "fin"), ("Economics, 1 line", "domain", "econ"),
         ("Near threshold", "near", "true"), ("Far from threshold", "near", "false"),
         ("Distractor flips answer", "distractor_flip", "true"), ("No flipping distractor", "distractor_flip", "false"),
         ("Two bounds", "shape", "between (2 bounds)"), ("One bound", "shape", "one-sided")]
for y, (label, col, val) in enumerate(feats[::-1]):
    r = get(col, val); c1, c4 = 100 * r["C1_direct"], 100 * r["C4_spec_code"]
    b.plot([c1, c4], [y, y], color=GRID, lw=2, zorder=1, solid_capstyle="round")
    b.scatter([c1], [y], s=40, color=C1, edgecolor="white", lw=1.2, zorder=3)
    b.scatter([c4], [y], s=40, color=C4, edgecolor="white", lw=1.2, zorder=4)
    b.text(107, y, f"+{c4 - c1:.0f}", va="center", ha="left", fontsize=7.8, color=INK2)
b.text(107, len(feats) - 0.35, "gain", va="center", ha="left", fontsize=7.8, color=INK2)
b.set_yticks(range(len(feats))); b.set_yticklabels([f[0] for f in feats[::-1]]); b.set_ylim(-0.6, len(feats) - 0.2)
style(b); b.set_title("(B) ALLaM 7B by item type", loc="left", fontsize=9, pad=8)
for yy in (1.5, 3.5, 5.5):
    b.axhline(yy, color=GRID, lw=0.6, ls=(0, (2, 2)))

out = ROOT / "docs"
fig.savefig(out / "m3_fig.svg", bbox_inches="tight", pad_inches=0.02, transparent=True)
fig.savefig(out / "m3_fig.png", dpi=220, bbox_inches="tight", pad_inches=0.02, facecolor="white")
print("wrote", out / "m3_fig.svg")
