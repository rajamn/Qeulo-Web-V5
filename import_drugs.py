# To Execute python manage.py shell
# from import_drugs import import_drugs
#import_drugs()
import sqlite3
from drugs.models import Drug
from django.db import transaction

SQLITE_DB_PATH = r'D:\quelo_web_development\Quelo-Web v4\drugs.db'  # ✅ Adjust path as needed

def import_drugs():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT drug_name, composition, uses, side_effects, manufacturer
        FROM drugs
        WHERE drug_name IS NOT NULL AND TRIM(drug_name) != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    inserted = 0
    skipped = 0

    with transaction.atomic():
        for row in rows:
            drug_name = row[0].strip()

            if Drug.objects.filter(
                drug_name__iexact=drug_name,
                hospital__isnull=True,
                added_by_doctor__isnull=True
            ).exists():
                skipped += 1
                continue

            drug = Drug(
                drug_name=drug_name,
                composition=row[1],
                uses=row[2],
                side_effects=row[3],
                manufacturer=row[4],
                hospital=None,
                added_by_doctor=None
            )
            try:
                drug.full_clean()  # Ensures model validations
                drug.save()
                inserted += 1
            except ValueError:
                skipped += 1

    print(f"✅ {inserted} drugs imported. ❎ {skipped} skipped (duplicates).")
