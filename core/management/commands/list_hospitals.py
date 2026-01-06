# core/management/commands/list_hospitals.py
import sys
import csv
import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.apps import apps


class Command(BaseCommand):
    help = "List hospitals (filter by id/phone/search; output as table/json/csv)."

    def add_arguments(self, parser):
        parser.add_argument("--id", dest="ids", type=int, action="append",
                            help="Filter by hospital id (repeatable)")
        parser.add_argument("--phone", dest="phones", action="append",
                            help="Filter by phone number (repeatable)")
        parser.add_argument("--search", help="Case-insensitive search in name/city/state/email/phone")
        parser.add_argument("--order", default="id",
                            help="Order by field (e.g. id, hospital_name, city, -created_at)")
        parser.add_argument("--limit", type=int, help="Limit number of rows")
        parser.add_argument("--fields", default="id,hospital_name,phone_num,city,state,email",
                            help="Comma-separated fields to show")
        parser.add_argument("--format", dest="fmt", choices=["table", "json", "csv"], default="table",
                            help="Output format")

    def handle(self, *args, **opts):
        Hospital = apps.get_model("core", "Hospital")

        fields = [f.strip() for f in opts["fields"].split(",") if f.strip()]
        # Validate fields against model
        valid_field_names = {f.name for f in Hospital._meta.get_fields()
                             if getattr(f, "concrete", False) and not f.many_to_many and not f.one_to_many}
        bad = [f for f in fields if f not in valid_field_names]
        if bad:
            self.stderr.write(self.style.ERROR(f"Invalid field(s): {', '.join(bad)}"))
            self.stderr.write(self.style.NOTICE(f"Valid fields: {', '.join(sorted(valid_field_names))}"))
            sys.exit(1)

        qs = Hospital.objects.all()

        if opts.get("ids"):
            qs = qs.filter(id__in=opts["ids"])
        if opts.get("phones"):
            qs = qs.filter(phone_num__in=opts["phones"])
        if s := opts.get("search"):
            q = (Q(hospital_name__icontains=s) |
                 Q(city__icontains=s) |
                 Q(state__icontains=s) |
                 Q(email__icontains=s) |
                 Q(phone_num__icontains=s))
            qs = qs.filter(q)

        # Order
        try:
            qs = qs.order_by(opts["order"])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Bad --order value '{opts['order']}': {e}"))
            sys.exit(1)

        # Limit
        if opts.get("limit"):
            qs = qs[:opts["limit"]]

        rows = []
        for obj in qs:
            row = []
            for f in fields:
                v = getattr(obj, f, "")
                row.append("" if v is None else str(v))
            rows.append(row)

        fmt = opts["fmt"]
        if fmt == "json":
            data = [dict(zip(fields, r)) for r in rows]
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            return

        if fmt == "csv":
            writer = csv.writer(sys.stdout)
            writer.writerow(fields)
            writer.writerows(rows)
            return

        # fmt == "table"
        self._print_table(fields, rows)

    def _print_table(self, headers, rows):
        if not rows:
            self.stdout.write(self.style.WARNING("No hospitals found."))
            return
        # column widths
        widths = [len(h) for h in headers]
        for r in rows:
            for i, cell in enumerate(r):
                widths[i] = max(widths[i], len(cell))

        def fmt_row(vals):
            return "  ".join(val.ljust(widths[i]) for i, val in enumerate(vals))

        sep = "  ".join("-" * w for w in widths)
        self.stdout.write(fmt_row(headers))
        self.stdout.write(sep)
        for r in rows:
            self.stdout.write(fmt_row(r))
