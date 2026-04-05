"""
Custom User model with email-based authentication and roles.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for email-based User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user: email as login, role-based access."""

    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
    ]

    CURRENCY_CHOICES = [
        ('KGS', 'Кыргызский сом (сом)'),
        ('KZT', 'Казахстанский тенге (₸)'),
        ('RUB', 'Российский рубль (₽)'),
        ('USD', 'Доллар США ($)'),
    ]

    username = None
    email = models.EmailField('Email', unique=True)
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='manager')
    company_name = models.CharField('Компания', max_length=255, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    currency = models.CharField('Валюта', max_length=3, choices=CURRENCY_CHOICES, default='KZT')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def currency_symbol(self):
        symbols = {
            'KGS': 'сом',
            'KZT': '₸',
            'RUB': '₽',
            'USD': '$'
        }
        return symbols.get(self.currency, '₸')
