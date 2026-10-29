"""Pull residential sales from 2024 onward out of DLD's full transaction history (two ~580 MB parts)."""
import sys
import pandas as pd
from pathlib import Path

SRC = [Path(p) for p in sys.argv[1:]]
OUT = Path("data/dld/hist_sales_2024on.csv")
COLS = ["transaction_id", "instance_date", "trans_group_en", "procedure_name_en", "reg_type_en", "property_usage_en",
        "property_type_en", "property_sub_type_en", "area_name_en", "master_project_en", "project_name_en", "project_number",
        "building_name_en", "rooms_en", "procedure_area", "actual_worth", "meter_sale_price", "load_timestamp"]

first, kept, seen = True, 0, {}
for src in SRC:
    for ch in pd.read_csv(src, usecols=COLS, dtype=str, chunksize=200_000):
        ch = ch[(ch.trans_group_en == "Sales") & (ch.property_usage_en == "Residential") & (ch.instance_date >= "2024-01-01")]
        kept += len(ch)
        for y, n in ch.instance_date.str[:4].value_counts().items():
            seen[y] = seen.get(y, 0) + n
        ch.to_csv(OUT, mode="w" if first else "a", header=first, index=False)
        first = False
print("kept", kept, dict(sorted(seen.items())))
