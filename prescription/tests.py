from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# … other imports …

User = get_user_model()

class PrescriptionPDFTest(TestCase):
    def setUp(self):
        # 1. Retrieve (or create) a user without invoking create_user() directly:
        #    e.g., your admin user created by manage.py createsuperuser,
        #    or just create a superuser which typically doesn’t require extra args:
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="pass"
        )

        # 2. Force-login them
        self.client = Client()
        self.client.force_login(self.user)

        # … now build doctor, patient, appointment, prescription, etc. as before …

    def test_prescription_pdf(self):
        url = reverse("prescription_pdf", args=[self.pres.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
