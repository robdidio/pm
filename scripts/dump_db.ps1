$ErrorActionPreference = "Stop"

if (-not (docker ps --format "{{.Names}}" | Select-String -Pattern "^pm-app$")) {
  Write-Error "pm-app container is not running. Start it with scripts/start.ps1."
}

$python = @'
import sqlite3
from textwrap import shorten

conn = sqlite3.connect("/app/data/pm.db")
cur = conn.cursor()

def dump_table(name, limit=5):
    rows = cur.execute(f"SELECT * FROM {name} LIMIT {limit}").fetchall()
    print(f"\n{name} ({len(rows)} rows shown)")
    for row in rows:
        print(shorten(str(row), width=160, placeholder="..."))

for table in ("users", "boards", "columns", "cards"):
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")

for table in ("users", "boards", "columns", "cards"):
    dump_table(table)
'@

$python | docker exec -i pm-app python -
