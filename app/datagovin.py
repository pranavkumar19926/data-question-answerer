"""data.gov.in adapter — drop any CSVs into data/raw/, run to rebuild DB + catalog stub.
Usage: python app/datagovin.py data/raw/myfile.csv --table mytable
       python app/datagovin.py --all   (loads every CSV in data/raw/)
Then edit app/catalog.json meanings in plain language (Must-Have #1).
"""
import re, sqlite3, sys, json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
DB = ROOT / "db" / "app.db"
CATALOG = Path(__file__).parent / "catalog.json"

def clean(col: str) -> str:
    c = re.sub(r"\W+", "_", col.strip().lower()).strip("_")
    return c or "col"

def load_csv(csv_path: Path, table: str):
    df = pd.read_csv(csv_path)
    df.columns = [clean(c) for c in df.columns]
    # cap size for demo
    if len(df) > 50000:
        print(f"Large file ({len(df)} rows), keeping first 50000 for demo.")
        df = df.head(50000)
    con = sqlite3.connect(DB)
    df.to_sql(table, con, if_exists="replace", index=False)
    con.close()
    print(f"OK: {table} <- {csv_path.name} ({len(df)} rows, {len(df.columns)} cols)")
    return list(df.columns)

def update_catalog(table: str, cols: list[str]):
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    cat["tables"] = [t for t in cat["tables"] if t["name"] != table]
    cat["tables"].append({
        "name": table,
        "description": f"EDIT ME: what is {table}? Which question does it answer?",
        "columns": [{"name": c, "type": "TEXT", "meaning": f"EDIT ME: what does {c} mean?"} for c in cols]})
    CATALOG.write_text(json.dumps(cat, indent=2), encoding="utf-8")
    print(f"Catalog stub added for '{table}'. Edit meanings in app/catalog.json.")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if args[0] == "--all":
        files = list((ROOT / "data" / "raw").glob("*.csv"))
        if not files: print("Put CSVs in data/raw/ first."); sys.exit(1)
        for f in files:
            cols = load_csv(f, clean(f.stem))
            update_catalog(clean(f.stem), cols)
    else:
        csv_path = Path(args[0])
        table = clean(args[2] if len(args) > 2 and args[1] == "--table" else csv_path.stem)
        cols = load_csv(csv_path, table)
        update_catalog(table, cols)
