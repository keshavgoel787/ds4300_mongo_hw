"""
DS4300 - MongoDB API
Dataset: CDC Social Vulnerability Index (King County, WA)

A PyMongo-based API that allows a data scientist to query the SVI dataset
without knowing MongoDB or the underlying schema.
"""

from pymongo import MongoClient

# ── connection ────────────────────────────────────────────────────────────────

_client = None

def _get_collection():
    """Return the svi collection, lazily opening a MongoClient on first call."""
    global _client
    if _client is None:
        _client = MongoClient("mongodb://localhost:27017/")
    return _client["ds4300"]["svi"]


# ── API functions ─────────────────────────────────────────────────────────────

def get_tracts_by_quintile(quintile: int) -> list[dict]:
    """
    Return all census tracts at a given vulnerability quintile (1–5).
    Quintile 1 = most vulnerable, Quintile 5 = least vulnerable.

    Args:
        quintile: Integer from 1 (most vulnerable) to 5 (least vulnerable).

    Returns:
        List of tract documents with geoid, condition_score, rpl_themes,
        and total population, sorted by condition_score ascending.

    Raises:
        ValueError: If quintile is not in the range 1–5.

    Example:
        tracts = get_tracts_by_quintile(1)
    """
    if quintile not in range(1, 6):
        raise ValueError("quintile must be between 1 and 5")
    col = _get_collection()
    results = col.find(
        {"vulnerability.quintile": quintile},
        {"_id": 0, "geography.geoid": 1, "vulnerability.condition_score": 1,
         "vulnerability.rpl_themes": 1, "population.total": 1}
    ).sort("vulnerability.condition_score", 1)
    return list(results)


def get_vulnerability_summary() -> list[dict]:
    """
    Return an aggregated summary for each vulnerability quintile.

    Each row contains:
        - quintile: the quintile number (1–5)
        - tract_count: number of census tracts in that quintile
        - total_population: sum of all residents in that quintile
        - avg_population: mean population per tract
        - avg_rpl_themes: mean CDC RPL Themes composite score
        - pct_flagged: percentage of tracts with at least one flagged factor

    Returns:
        List of summary dicts sorted by quintile ascending.

    Example:
        summary = get_vulnerability_summary()
        for row in summary:
            print(row)
    """
    col = _get_collection()
    pipeline = [
        {"$group": {
            "_id": "$vulnerability.quintile",
            "tract_count":       {"$sum": 1},
            "total_population":  {"$sum": "$population.total"},
            "avg_population":    {"$avg": "$population.total"},
            "avg_rpl_themes":    {"$avg": "$vulnerability.rpl_themes"},
            "flagged_tracts":    {"$sum": "$vulnerability.f_total"},
        }},
        {"$addFields": {
            "pct_flagged": {
                "$multiply": [
                    {"$divide": ["$flagged_tracts", "$tract_count"]},
                    100
                ]
            }
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "quintile": "$_id", "tract_count": 1,
                      "total_population": 1, "avg_population": 1,
                      "avg_rpl_themes": 1, "pct_flagged": 1}}
    ]
    return list(col.aggregate(pipeline))


def get_top_n_vulnerable_tracts(n: int = 10) -> list[dict]:
    """
    Return the N most socially vulnerable census tracts.

    Tracts are ranked by condition_score ascending (lower = more vulnerable).

    Args:
        n: Number of tracts to return (default 10).

    Returns:
        List of tract documents with geoid, condition_score, quintile,
        and total population.

    Example:
        worst = get_top_n_vulnerable_tracts(5)
    """
    col = _get_collection()
    results = col.find(
        {},
        {"_id": 0, "geography.geoid": 1, "vulnerability.condition_score": 1,
         "vulnerability.quintile": 1, "population.total": 1}
    ).sort("vulnerability.condition_score", 1).limit(n)
    return list(results)


def get_population_at_risk(max_quintile: int = 2) -> dict:
    """
    Return the total population living in the most vulnerable census tracts.

    "At risk" is defined as quintile <= max_quintile.

    Args:
        max_quintile: Upper quintile bound (inclusive). Default is 2, capturing
                      the two most vulnerable groups.

    Returns:
        Dict with keys total_population_at_risk and tract_count,
        or an empty dict if no matching tracts are found.

    Raises:
        ValueError: If max_quintile is not in the range 1–5.

    Example:
        at_risk = get_population_at_risk(max_quintile=2)
        print(at_risk["total_population_at_risk"])
    """
    if max_quintile not in range(1, 6):
        raise ValueError("max_quintile must be between 1 and 5")
    col = _get_collection()
    pipeline = [
        {"$match": {"vulnerability.quintile": {"$lte": max_quintile}}},
        {"$group": {
            "_id": None,
            "total_population_at_risk": {"$sum": "$population.total"},
            "tract_count": {"$sum": 1}
        }},
        {"$project": {"_id": 0, "total_population_at_risk": 1, "tract_count": 1}}
    ]
    result = list(col.aggregate(pipeline))
    return result[0] if result else {}


# ── demo + visualization ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import os
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    print("=== Top 5 Most Vulnerable Tracts ===")
    for t in get_top_n_vulnerable_tracts(5):
        print(json.dumps(t, indent=2))

    print("\n=== Vulnerability Summary by Quintile ===")
    for row in get_vulnerability_summary():
        print(json.dumps(row, indent=2))

    print("\n=== Population at Risk (Quintile 1-2) ===")
    print(json.dumps(get_population_at_risk(2), indent=2))

    print("\n=== Quintile 1 Tracts (first 3) ===")
    for t in get_tracts_by_quintile(1)[:3]:
        print(json.dumps(t, indent=2))

    # ── visualization ─────────────────────────────────────────────────────────
    summary = get_vulnerability_summary()

    quintiles   = [row["quintile"]         for row in summary]
    total_pop   = [row["total_population"] for row in summary]
    pct_flagged = [row["pct_flagged"]      for row in summary]
    avg_rpl     = [row["avg_rpl_themes"]   for row in summary]

    COLORS = ["#d73027", "#f46d43", "#fdae61", "#74add1", "#313695"]
    LABELS = [f"Q{q}" for q in quintiles]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "CDC Social Vulnerability Index — King County, WA (2018)",
        fontsize=14, fontweight="bold", y=1.01
    )

    # Panel 1: Total population per quintile
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

    # Panel 2: % flagged tracts + avg RPL score
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
    ax2.legend([bars2, line], ["% Flagged tracts", "Avg RPL Themes score"],
               fontsize=8, loc="upper right")

    plt.tight_layout()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "svi_visualization.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved figure to {out_path}")
    plt.show()
