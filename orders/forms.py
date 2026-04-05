"""
Order forms.
"""
from django import forms
from .models import Order
from crm.models import Client


class OrderForm(forms.ModelForm):
    """Form for creating/editing orders."""

    class Meta:
        model = Order
        fields = ['client', 'status', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-input', 'id': 'order-client'}),
            'status': forms.Select(attrs={'class': 'form-input', 'id': 'order-status'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Примечание', 'id': 'order-notes'}),
        }
