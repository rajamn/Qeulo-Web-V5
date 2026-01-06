from django.core.management.base import BaseCommand
from django.http import HttpRequest

class Command(BaseCommand):
    help = "Debug what Django sees for Host and scheme headers."

    def handle(self, *args, **options):
        # Simulate a request object
        request = HttpRequest()
        request.META["HTTP_HOST"] = "quelo.in"
        request.META["HTTP_X_FORWARDED_PROTO"] = "https"

        self.stdout.write(self.style.SUCCESS("=== Django Request Debug ==="))
        self.stdout.write(f"Host: {request.get_host()}")
        self.stdout.write(f"Scheme: {request.scheme}")
        self.stdout.write(f"is_secure: {request.is_secure()}")
