"""
Forms for supplier and purchase order management.
"""
from django import forms
from .models import Supplier, PurchaseOrder


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_name', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название поставщика'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ФИО контактного лица'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 (___) ___-____'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Адрес'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Заметки'}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'invoice_number', 'paid_amount', 'notes']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Номер накладной (необязательно)'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'value': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Примечание'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['supplier'].queryset = Supplier.objects.filter(user=user)
        self.fields['supplier'].widget.attrs['class'] = 'form-input'
        self.fields['supplier'].empty_label = '— Без поставщика —'
        self.fields['supplier'].required = False
