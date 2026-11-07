"""Reshape Crops_data.csv (wide, district-level) to long tidy table.
Source mirror: https://github.com/nileshiq/Crop-Datasets-for-All-Indian-States (Crops_data.csv)
Origin: data.gov.in APY-style district crop data (India, 2010-2017 per repo).
Units preserved: area in 1000 ha, production in 1000 tons, yield in kg/ha.
Run: python app/load_real.py
"""
import re, sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
CSV = ROOT / "data" / "raw" / "Crops_data.csv"
DB = ROOT / "db" / "app.db"

df = pd.read_csv(CSV)
id_cols = ["Dist Code", "Year", "State Code", "State Name", "Dist Name"]
meas = [c for c in df.columns if c not in id_cols]
triples: dict = {}
for c in meas:
    m = re.match(r"^(.*) (AREA \(1000 ha\)|PRODUCTION \(1000 tons\)|YIELD \(Kg per ha\))$", c)
    crop, kind = m.group(1).strip(), m.group(2)
    key = {"AREA (1000 ha)": "area", "PRODUCTION (1000 tons)": "prod", "YIELD (Kg per ha)": "yield"}[kind]
    triples.setdefault(crop, {})[key] = c

rows = []
for crop, d in triples.items():
    if set(d) != {"area", "prod", "yield"}:
        continue
    sub = df[["State Name", "Dist Name", "Year"]].copy()
    sub["crop"] = crop.title()
    sub["area_1000ha"] = df[d["area"]]
    sub["production_1000tons"] = df[d["prod"]]
    sub["yield_kgpha"] = df[d["yield"]]
    rows.append(sub)
long = pd.concat(rows, ignore_index=True)
long.columns = ["state_name", "dist_name", "year", "crop", "area_1000ha", "production_1000tons", "yield_kgpha"]
long = long.dropna(subset=["production_1000tons"])
long = long[long["production_1000tons"] > 0]

con = sqlite3.connect(DB)
long.to_sql("real_crop_production", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS idx_real_scys ON real_crop_production(state_name, crop, year)")
n = con.execute("SELECT COUNT(*) FROM real_crop_production").fetchone()[0]
yrs = con.execute("SELECT MIN(year), MAX(year) FROM real_crop_production").fetchone()
sts = con.execute("SELECT COUNT(DISTINCT state_name) FROM real_crop_production").fetchone()[0]
crs = con.execute("SELECT COUNT(DISTINCT crop) FROM real_crop_production").fetchone()[0]
con.commit(); con.close()
print(f"OK real_crop_production: {n} rows, years {yrs[0]}-{yrs[1]}, {sts} states, {crs} crops")
print("Crops:", ", ".join(sorted(pd.read_sql('SELECT DISTINCT crop FROM real_crop_production', sqlite3.connect(DB))['crop'].tolist())[:40]))
