"""
CRM forms for client management.
"""
from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    """Form for creating/editing clients."""

    class Meta:
        model = Client
        fields = ['name', 'phone', 'email', 'company_name', 'address', 'discount_percent', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ФИО клиента', 'id': 'client-name'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 (___) ___-____', 'id': 'client-phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@example.com', 'id': 'client-email'}),
            'company_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название компании', 'id': 'client-company'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Адрес', 'id': 'client-address'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0', 'max': '100', 'placeholder': '0', 'id': 'client-discount'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Заметки', 'id': 'client-notes'}),
        }
