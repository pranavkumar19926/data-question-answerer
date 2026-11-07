"""Load toy data.gov.in-style dataset into SQLite.
Tables: states, crops, production (allows JOINs, totals, filters).
Run: python app/load_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

states = [
    (1, "Punjab", "North", 50362),
    (2, "Maharashtra", "West", 307713),
    (3, "West Bengal", "East", 88752),
    (4, "Tamil Nadu", "South", 130058),
    (5, "Uttar Pradesh", "North", 243286),
    (6, "Madhya Pradesh", "Central", 308245),
]
crops = [
    (1, "Rice", "Kharif"),
    (2, "Wheat", "Rabi"),
    (3, "Sugarcane", "Annual"),
    (4, "Cotton", "Kharif"),
    (5, "Soybean", "Kharif"),
]
# (state_id, crop_id, year, area_ha, production_tonnes)
production = [
    (1, 2, 2022, 3500000, 19500000), (1, 1, 2022, 3100000, 13800000),
    (1, 1, 2021, 3050000, 13200000), (1, 2, 2021, 3480000, 18900000),
    (5, 2, 2022, 9800000, 36000000), (5, 1, 2022, 5900000, 15500000),
    (5, 3, 2022, 2200000, 178000000), (5, 2, 2021, 9700000, 34500000),
    (2, 4, 2022, 4200000, 7800000), (2, 5, 2022, 5100000, 6400000),
    (2, 1, 2022, 1500000, 3200000), (2, 5, 2021, 4900000, 5900000),
    (3, 1, 2022, 5400000, 16000000), (3, 1, 2021, 5300000, 15200000),
    (4, 1, 2022, 2100000, 7500000), (4, 3, 2022, 230000, 21000000),
    (6, 2, 2022, 6000000, 20000000), (6, 5, 2022, 6200000, 7500000),
    (6, 4, 2022, 1800000, 2800000), (6, 2, 2021, 5900000, 19200000),
]

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.executescript("DROP TABLE IF EXISTS production; DROP TABLE IF EXISTS states; DROP TABLE IF EXISTS crops;")
cur.execute("CREATE TABLE states(state_id INTEGER PRIMARY KEY, state_name TEXT, region TEXT, area_sqkm INTEGER)")
cur.execute("CREATE TABLE crops(crop_id INTEGER PRIMARY KEY, crop_name TEXT, season TEXT)")
cur.execute("""CREATE TABLE production(
 state_id INTEGER, crop_id INTEGER, year INTEGER,
 area_ha INTEGER, production_tonnes REAL,
 FOREIGN KEY(state_id) REFERENCES states(state_id),
 FOREIGN KEY(crop_id) REFERENCES crops(crop_id))""")
cur.executemany("INSERT INTO states VALUES(?,?,?,?)", states)
cur.executemany("INSERT INTO crops VALUES(?,?,?)", crops)
cur.executemany("INSERT INTO production VALUES(?,?,?,?,?)", production)
con.commit()
count = cur.execute('SELECT COUNT(*) FROM production').fetchone()[0]
print(f"OK: {count} production rows loaded.")
con.close()
