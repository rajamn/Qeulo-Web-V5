# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from datetime import date
from quelo_backend import settings
from django.utils.text import slugify


class Role(models.Model):
    ROLE_HOSPITAL_ADMIN = "hospital_admin"
    ROLE_RECEPTION = "reception"
    ROLE_DOCTOR = "doctor"
    ROLE_ACCOUNTANT = "accountant"
    ROLE_SUPER_ADMIN = "super_admin"

    ROLES = [
        ROLE_HOSPITAL_ADMIN,
        ROLE_RECEPTION,
        ROLE_DOCTOR,
        ROLE_ACCOUNTANT,
        ROLE_SUPER_ADMIN,
    ]

    role_name = models.CharField(
        max_length=50,
        unique=True,
        choices=[(r, r) for r in ROLES]
    )

    def __str__(self):
        return self.role_name



class Hospital(models.Model):
    hospital_name = models.CharField(max_length=255, default="Unnamed Hospital")
    phone_num     = models.CharField(max_length=20, unique=True)
    street        = models.CharField(max_length=255, blank=True, null=True)
    city          = models.CharField(max_length=100, blank=True, null=True)
    state         = models.CharField(max_length=100, blank=True, null=True)
    pincode       = models.CharField(max_length=20, blank=True, null=True)
    email         = models.EmailField(max_length=255, unique=True)
    name          = models.CharField(max_length=255)
    ai_enabled    = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    # 🆕 Slug field
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate slug only if not already set
        if not self.slug:
            base_slug = slugify(self.hospital_name)
            slug = base_slug
            counter = 1
            while Hospital.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


    def __str__(self):
        return self.hospital_name


class HospitalUserManager(BaseUserManager):
    
    def create_user(self, mobile_num, user_name, password=None, **extra_fields):
        if not mobile_num:
            raise ValueError('Mobile number is required')
        extra_fields.setdefault('display_name', user_name)

        # Pull the default password from settings, with a fallback
        default_pw = getattr(settings, 'DEFAULT_USER_PASSWORD', 'changeme123')
        pw = password or default_pw

        user = self.model(mobile_num=mobile_num, user_name=user_name, **extra_fields)
        user.set_password(pw)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_num, user_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(mobile_num, user_name, password, **extra_fields)



class HospitalUser(AbstractBaseUser, PermissionsMixin):
    mobile_num = models.CharField(max_length=20, unique=True)
    user_name  = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255,blank=True,null=True,
                                    help_text="Optional name shown in the UI")
    consult_validity_days = models.PositiveIntegerField(default=6)
    consult_validity_visits = models.PositiveIntegerField(default=2)
    consult_message_template = models.CharField(
        max_length=255,
        default="Valid for {days} days or {visits} visits whichever is earlier"
    )
    
    @property
    def display(self):
        return self.display_name or self.user_name

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='users'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True
    )

    doctor = models.OneToOneField(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked Doctor profile (if this user is a doctor)"
    )

    must_change_password = models.BooleanField(default=True)
    is_active            = models.BooleanField(default=True)
    is_staff             = models.BooleanField(default=False)

    objects = HospitalUserManager()

    USERNAME_FIELD  = 'mobile_num'
    REQUIRED_FIELDS = ['user_name']

    def __str__(self):
        return f"{self.user_name} ({self.mobile_num})"
