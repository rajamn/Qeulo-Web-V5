# quick local exporter (run outside Django)
import sqlite3, csv, pathlib
p = pathlib.Path("drugs.csv")
conn = sqlite3.connect(r"D:\quelo_web_development\Quelo-Web v4\drugs.db")
cur = conn.cursor()
cur.execute("""
  SELECT DISTINCT drug_name, composition, uses, side_effects, manufacturer
  FROM drugs WHERE drug_name IS NOT NULL AND TRIM(drug_name)!=''
""")
with p.open("w", newline='', encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["drug_name","composition","uses","side_effects","manufacturer"])
  w.writerows(cur.fetchall())
conn.close()
print("Wrote", p.resolve())
