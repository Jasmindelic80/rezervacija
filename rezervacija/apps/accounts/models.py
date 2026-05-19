import random
import string
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    ROLE_CLIENT = 'client'
    ROLE_PROVIDER = 'provider'
    ROLES = [
        (ROLE_CLIENT, 'Client'),
        (ROLE_PROVIDER, 'Service Provider'),
    ]

    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_CLIENT)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)

    def is_provider(self):
        return self.role == self.ROLE_PROVIDER

    def __str__(self):
        return self.phone or self.username


class PhoneOTP(models.Model):
    phone = models.CharField(max_length=20)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('register', 'Registration'),
            ('login', 'Login'),
            ('reset', 'Password Reset'),
        ],
        default='register'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def is_valid(self):
        return not self.verified and not self.is_expired() and self.attempts < 5

    @classmethod
    def generate_otp(cls):
        return ''.join(random.choices(string.digits, k=6))

    @classmethod
    def create_for_phone(cls, phone, purpose='register'):
        cls.objects.filter(phone=phone, purpose=purpose, verified=False).delete()
        otp = cls.generate_otp()
        return cls.objects.create(phone=phone, otp=otp, purpose=purpose)

    def __str__(self):
        return f"OTP {self.phone} [{self.purpose}]"