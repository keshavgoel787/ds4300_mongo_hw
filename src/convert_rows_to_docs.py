"""
Convert rows.json (Socrata flat-array format) into a proper JSON array
of nested documents suitable for mongoimport.

Input:  data/rows.json
Output: processed/docs.json

Document structure:
{
  "year": 2018,
  "geography": {
    "geoid": "53033001702",
    "type": "County",
    "name": "King County"
  },
  "population": {
    "total": 4832,
    "condition_weighted": 2708.82
  },
  "vulnerability": {
    "condition_score": 56.06,
    "rpl_themes": 0.4394,
    "quintile": 3,
    "f_total": 0,
    "weighted_avg_quintile": 0.634,
    "not_socially_vulnerable": false
  },
  "shape": {
    "area": 13779306.64,
    "length": 17476.41
  }
}
"""

import json

INPUT  = "data/rows.json"
OUTPUT = "processed/docs.json"

SYSTEM_COL_COUNT = 8
SKIP_FIELDS = {"the_geom", "objectid"}


def coerce(value, dtype):
    """Cast string values to appropriate Python types."""
    if value is None:
        return None
    if dtype == "number":
        try:
            f = float(value)
            return int(f) if f == int(f) else f
        except (ValueError, TypeError):
            return value
    return value


def build_doc(flat):
    """Reshape a flat field dict into a nested document."""
    return {
        "year": flat.get("year"),
        "geography": {
            "geoid": str(flat.get("featureid", "")),
            "type": flat.get("geography"),
            "name": flat.get("name_geography"),
        },
        "population": {
            "total": flat.get("totalpopulation"),
            "condition_weighted": flat.get("condition_totalpop"),
        },
        "vulnerability": {
            "condition_score": flat.get("condition"),
            "rpl_themes": flat.get("rpl_themes"),
            "quintile": flat.get("quintile"),
            "f_total": flat.get("f_total"),
            "weighted_avg_quintile": flat.get("weightedavgquintile"),
            "not_socially_vulnerable": bool(flat.get("notsociallyvulnerable")),
        },
        "shape": {
            "area": flat.get("shape__area"),
            "length": flat.get("shape__length"),
        },
    }


def main():
    with open(INPUT) as f:
        raw = json.load(f)

    columns = raw["meta"]["view"]["columns"]
    data_cols = columns[SYSTEM_COL_COUNT:]

    docs = []
    for row in raw["data"]:
        data_values = row[SYSTEM_COL_COUNT:]
        flat = {}
        for col, val in zip(data_cols, data_values):
            name = col["fieldName"]
            if name in SKIP_FIELDS:
                continue
            flat[name] = coerce(val, col["dataTypeName"])
        docs.append(build_doc(flat))

    with open(OUTPUT, "w") as f:
        json.dump(docs, f, indent=2)

    print(f"Wrote {len(docs)} documents to {OUTPUT}")
    print("Sample document:")
    print(json.dumps(docs[0], indent=2))


if __name__ == "__main__":
    main()
