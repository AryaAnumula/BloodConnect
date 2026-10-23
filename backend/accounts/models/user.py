"""Shared foundational schema. Arnav owns structural edits; Ankitha reviews consumers."""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('A superuser must have Django staff and superuser flags.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        DONOR = 'DONOR', 'Donor'
        STAFF = 'STAFF', 'Staff'
        REQUESTER = 'REQUESTER', 'Hospital/requester'
        ADMIN = 'ADMIN', 'Administrator'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.DONOR)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        permissions = [('view_donor_health', 'Can view donor health information under approved staff policy')]

    def __str__(self):
        return str(self.id)  # Avoid implicit email/health-data logging.
