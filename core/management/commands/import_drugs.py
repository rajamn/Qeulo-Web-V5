import csv
from pathlib import Path
from typing import Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from drugs.models import Drug


REQUIRED_COLS = {"drug_name"}
# Optional CSV columns we’ll read if present:
OPTIONAL_COLS = {
    "composition", "uses", "side_effects", "manufacturer",
    "dosage", "frequency", "duration",
}


class Command(BaseCommand):
    help = "Import drugs from a CSV file into the global drug library (hospital=None, added_by_doctor=None)."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to drugs.csv")
        parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default: utf-8)")
        parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
        parser.add_argument("--limit", type=int, default=None, help="Import at most N rows (useful for testing).")
        parser.add_argument("--dry-run", action="store_true", help="Parse and validate, but do not write to DB.")

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        encoding = opts["encoding"]
        delimiter = opts["delimiter"]
        limit = opts["limit"]
        dry_run = opts["dry_run"]

        self.stdout.write(self.style.NOTICE(f"Reading: {csv_path}"))
        self.stdout.write(self.style.NOTICE(f"Options: encoding={encoding}, delimiter='{delimiter}', dry_run={dry_run}, limit={limit}"))

        # Load existing GLOBAL drugs (hospital=None & added_by_doctor=None) for fast duplicate checks.
        existing: Set[str] = set(
            Drug.objects.filter(hospital__isnull=True, added_by_doctor__isnull=True)
                        .values_list("drug_name", flat=True)
        )
        existing = {(n or "").strip().lower() for n in existing}

        inserted = 0
        skipped  = 0
        seen_in_batch: Set[str] = set()  # Avoid duplicates within the CSV itself

        # Use a transaction for integrity; no commit if dry-run.
        ctx = transaction.atomic
        with ctx():
            with csv_path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delimiter)

                # Validate header
                header = {h.strip() for h in reader.fieldnames or []}
                missing = REQUIRED_COLS - header
                if missing:
                    raise CommandError(f"CSV missing required columns: {', '.join(sorted(missing))}")

                count = 0
                for row in reader:
                    if limit is not None and count >= limit:
                        break
                    count += 1

                    # Normalize name
                    raw_name = (row.get("drug_name") or "").strip()
                    if not raw_name:
                        skipped += 1
                        continue

                    key = raw_name.lower()
                    if key in existing or key in seen_in_batch:
                        skipped += 1
                        continue

                    # Build Drug instance with optional fields if present
                    kwargs = {
                        "drug_name": raw_name,
                        "hospital": None,
                        "added_by_doctor": None,
                    }
                    for col in OPTIONAL_COLS:
                        if col in row:
                            val = (row.get(col) or "").strip() or None
                            kwargs[col] = val

                    d = Drug(**kwargs)

                    try:
                        # Your model's save() enforces scope-duplicate rules — keep per-row save.
                        d.full_clean()
                        if not dry_run:
                            d.save()
                        inserted += 1
                        seen_in_batch.add(key)
                    except ValueError:
                        # Duplicate in scope or model-level guard tripped
                        skipped += 1

            if dry_run:
                # Ensure nothing is written when --dry-run is used.
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"✅ Imported: {inserted}"))
        self.stdout.write(self.style.WARNING(f"⏭️  Skipped:  {skipped}"))
        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry run complete. No changes were committed."))
