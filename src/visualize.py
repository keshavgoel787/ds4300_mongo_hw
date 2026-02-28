"""
DS4300 - Visualization
Generates a two-panel figure from the CDC SVI API and saves it to outputs/.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from api import get_vulnerability_summary

os.makedirs("outputs", exist_ok=True)

summary = get_vulnerability_summary()

quintiles     = [row["quintile"]          for row in summary]
total_pop     = [row["total_population"]  for row in summary]
pct_flagged   = [row["pct_flagged"]       for row in summary]
avg_rpl       = [row["avg_rpl_themes"]    for row in summary]

COLORS = ["#d73027", "#f46d43", "#fdae61", "#74add1", "#313695"]
LABELS = [f"Q{q}" for q in quintiles]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle(
    "CDC Social Vulnerability Index — King County, WA (2018)",
    fontsize=14, fontweight="bold", y=1.01
)

# ── Panel 1: Total population per quintile ────────────────────────────────────
bars = ax1.bar(LABELS, total_pop, color=COLORS, edgecolor="white", linewidth=0.8)
ax1.axhline(sum(total_pop) / len(total_pop), color="black",
            linestyle="--", linewidth=1, label="Mean across quintiles")
ax1.set_title("Total Population by Vulnerability Quintile", fontsize=11)
ax1.set_xlabel("Vulnerability Quintile  (Q1 = most vulnerable)", fontsize=9)
ax1.set_ylabel("Total Population", fontsize=9)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax1.legend(fontsize=8)
for bar, val in zip(bars, total_pop):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2000,
             f"{val:,}", ha="center", va="bottom", fontsize=8)

# ── Panel 2: % flagged tracts + avg RPL score ─────────────────────────────────
ax2b = ax2.twinx()
bars2 = ax2.bar(LABELS, pct_flagged, color=COLORS, edgecolor="white",
                linewidth=0.8, label="% Flagged tracts")
line, = ax2b.plot(LABELS, avg_rpl, color="black", marker="o",
                  linewidth=2, markersize=6, label="Avg RPL Themes score")
ax2.set_title("Flagged Tracts & Avg RPL Score by Quintile", fontsize=11)
ax2.set_xlabel("Vulnerability Quintile  (Q1 = most vulnerable)", fontsize=9)
ax2.set_ylabel("% of Tracts with Flagged Vulnerability Factor", fontsize=9)
ax2b.set_ylabel("Avg RPL Themes Score (higher = more vulnerable)", fontsize=9)
ax2.set_ylim(0, 115)
ax2b.set_ylim(0, 1.1)
lines = [bars2, line]
labels = ["% Flagged tracts", "Avg RPL Themes score"]
ax2.legend(lines, labels, fontsize=8, loc="upper right")

plt.tight_layout()
out_path = "../outputs/svi_visualization.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved figure to {out_path}")
plt.show()
