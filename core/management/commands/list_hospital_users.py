# core/management/commands/list_hospital_users.py
import sys
import csv
import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.apps import apps


class Command(BaseCommand):
    help = "List HospitalUser rows for a given hospital (by --hospital-id or --hospital-phone)."

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group(required=True)
        grp.add_argument("--hospital-id", type=int, help="Hospital id to list users for")
        grp.add_argument("--hospital-phone", help="Hospital phone to list users for")

        parser.add_argument("--role", action="append",
                            help="Filter by role name (repeatable)")
        parser.add_argument("--active", choices=["1", "0"],
                            help="Filter by is_active (1 or 0)")
        parser.add_argument("--doctor-only", action="store_true",
                            help="Only include users linked to a doctor")
        parser.add_argument("--search",
                            help="Case-insensitive search in mobile_num/user_name/display_name")

        parser.add_argument(
            "--fields",
            default="id,mobile_num,user_name,display_name,role,hospital_id,doctor_id,is_active",
            help=("Comma-separated fields to display. "
                  "Available: id,mobile_num,user_name,display_name,role,hospital_id,hospital,"
                  "doctor_id,is_active,is_staff,must_change_password")
        )
        parser.add_argument(
            "--order",
            default="mobile_num",
            help=("Order by one of: id,mobile_num,user_name,display_name,role,hospital,doctor_id "
                  "(prefix with '-' for descending)")
        )
        parser.add_argument("--limit", type=int, help="Limit number of rows")
        parser.add_argument("--format", dest="fmt", choices=["table", "json", "csv"], default="table",
                            help="Output format")

    def handle(self, *args, **opts):
        Hospital = apps.get_model("core", "Hospital")
        HospitalUser = apps.get_model("core", "HospitalUser")

        # --- resolve hospital ---
        try:
            if opts.get("hospital_id") is not None:
                hospital = Hospital.objects.get(id=opts["hospital_id"])
            else:
                hospital = Hospital.objects.get(phone_num=opts["hospital_phone"])
        except Hospital.DoesNotExist:
            key = ("id=" + str(opts["hospital_id"])) if opts.get("hospital_id") is not None \
                  else ("phone=" + str(opts["hospital_phone"]))
            self.stderr.write(self.style.ERROR(f"No hospital found ({key})"))
            sys.exit(1)

        # --- base queryset ---
        qs = (
            HospitalUser.objects
            .filter(hospital=hospital)
            .select_related("hospital", "role", "doctor")
        )

        # filters
        if roles := opts.get("role"):
            qs = qs.filter(role__role_name__in=roles)
        if opts.get("active") is not None:
            qs = qs.filter(is_active=(opts["active"] == "1"))
        if opts.get("doctor_only"):
            qs = qs.filter(doctor__isnull=False)
        if s := opts.get("search"):
            qs = qs.filter(
                Q(mobile_num__icontains=s) |
                Q(user_name__icontains=s) |
                Q(display_name__icontains=s)
            )

        # ordering (map friendly keys to ORM paths)
        order_key = opts["order"]
        desc = order_key.startswith("-")
        key = order_key[1:] if desc else order_key
        order_map = {
            "id": "id",
            "mobile_num": "mobile_num",
            "user_name": "user_name",
            "display_name": "display_name",
            "role": "role__role_name",
            "hospital": "hospital__hospital_name",
            "doctor_id": "doctor_id",
        }
        if key not in order_map:
            self.stderr.write(self.style.ERROR(f"Bad --order value '{order_key}'"))
            self.stderr.write(self.style.NOTICE("Allowed: " + ", ".join(order_map.keys())))
            sys.exit(1)
        qs = qs.order_by(("-" if desc else "") + order_map[key])

        if opts.get("limit"):
            qs = qs[:opts["limit"]]

        # field extractors (also allow related-friendly labels)
        def b(v):  # bool -> '1'/'0'
            return "1" if v else "0"

        FIELDS = {
            "id":               lambda u: str(u.id),
            "mobile_num":       lambda u: u.mobile_num or "",
            "user_name":        lambda u: u.user_name or "",
            "display_name":     lambda u: u.display_name or "",
            "role":             lambda u: (u.role.role_name if u.role else ""),
            "hospital_id":      lambda u: str(u.hospital_id),
            "hospital":         lambda u: u.hospital.hospital_name if u.hospital_id else "",
            "doctor_id":        lambda u: (str(u.doctor_id) if u.doctor_id else ""),
            "is_active":        lambda u: b(u.is_active),
            "is_staff":         lambda u: b(u.is_staff),
            "must_change_password": lambda u: b(u.must_change_password),
        }

        fields = [f.strip() for f in opts["fields"].split(",") if f.strip()]
        unknown = [f for f in fields if f not in FIELDS]
        if unknown:
            self.stderr.write(self.style.ERROR(f"Invalid field(s): {', '.join(unknown)}"))
            self.stderr.write(self.style.NOTICE("Valid: " + ", ".join(sorted(FIELDS.keys()))))
            sys.exit(1)

        rows = [[FIELDS[f](u) for f in fields] for u in qs]

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

        # table
        self._print_table(fields, rows)

    def _print_table(self, headers, rows):
        if not rows:
            self.stdout.write(self.style.WARNING("No users found."))
            return
        widths = [len(h) for h in headers]
        for r in rows:
            for i, cell in enumerate(r):
                widths[i] = max(widths[i], len(cell or ""))

        def fmt_row(vals):
            return "  ".join((vals[i] or "").ljust(widths[i]) for i in range(len(vals)))

        sep = "  ".join("-" * w for w in widths)
        self.stdout.write(fmt_row(headers))
        self.stdout.write(sep)
        for r in rows:
            self.stdout.write(fmt_row(r))
