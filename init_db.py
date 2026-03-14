import sqlite3, pandas as pd, os

DB = "gate_ga.db"

SHEETS = {
    "Quantitative": "data/quantitative_sheet2.csv",
    "Verbal":       "data/verbal_sheet2.csv",
    "Spatial":      "data/spatial_sheet2.csv",
    "Analytical":   "data/analytical_sheet2.csv",
}

conn = sqlite3.connect(DB)
c = conn.cursor()

c.executescript("""
    DROP TABLE IF EXISTS questions;
    DROP TABLE IF EXISTS progress;

    CREATE TABLE questions (
        id       TEXT PRIMARY KEY,
        title    TEXT,
        url      TEXT,
        tags     TEXT,
        topic    TEXT,
        category TEXT
    );

    CREATE TABLE progress (
        user        TEXT,
        question_id TEXT,
        solved      INTEGER DEFAULT 0,
        revision    INTEGER DEFAULT 0,
        PRIMARY KEY (user, question_id)
    );
""")
conn.commit()

total = 0
for cat, path in SHEETS.items():
    if not os.path.exists(path):
        print(f"⚠️  Skipping {cat} — file not found: {path}")
        continue
    df = pd.read_csv(path)
    df["id"] = df["id"].astype(str)
    for _, row in df.iterrows():
        c.execute(
            "INSERT OR REPLACE INTO questions VALUES (?,?,?,?,?,?)",
            (str(row["id"]), str(row.get("title","")),
             str(row.get("url","")),  str(row.get("tags","")),
             str(row.get("topic","")), cat)
        )
    conn.commit()
    print(f"✅ {cat}: {len(df)} questions loaded")
    total += len(df)

conn.close()
print(f"\n🎉 Done! {total} total questions → {DB}")
