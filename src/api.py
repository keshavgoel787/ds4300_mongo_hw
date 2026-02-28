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
    global _client
    if _client is None:
        _client = MongoClient("mongodb://localhost:27017/")
    return _client["ds4300"]["svi"]


# ── API functions ─────────────────────────────────────────────────────────────

def get_tracts_by_quintile(quintile: int) -> list[dict]:
    """
    Return all census tracts at a given vulnerability quintile (1–5).
    Quintile 1 = most vulnerable, Quintile 5 = least vulnerable.

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
    Return a summary for each vulnerability quintile:
      - number of tracts
      - total and average population
      - average RPL themes score
      - proportion of tracts with flagged vulnerability factors

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
    Return the N most socially vulnerable census tracts,
    ranked by condition score (lowest score = most vulnerable).

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
    Return the total population living in census tracts at or below
    `max_quintile` (i.e., in the most vulnerable groups).

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


# ── demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

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
