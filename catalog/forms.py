"""
Catalog forms for product CRUD, import, and price levels.
"""
from django import forms
from .models import Product, Category, PriceLevel, CarMake, CarModel


class ProductForm(forms.ModelForm):
    """Form for creating/editing products."""

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['category'].queryset = Category.objects.filter(user=self.user)
            self.fields['analogs'].queryset = Product.objects.filter(user=self.user)
            self.fields['compatible_models'].queryset = CarModel.objects.filter(user=self.user)

    class Meta:
        model = Product
        fields = [
            'oem_number', 'part_number', 'name', 'category', 'brand', 'barcode',
            'description', 'price_purchase', 'compatible_models', 'analogs',
            'stock_quantity', 'min_stock', 'location', 'is_active'
        ]
        widgets = {
            'oem_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'OEM номер', 'id': 'product-oem'}),
            'part_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Артикул', 'id': 'product-partnum'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название товара', 'id': 'product-name'}),
            'category': forms.Select(attrs={'class': 'form-input', 'id': 'product-category'}),
            'brand': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Бренд', 'id': 'product-brand'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Штрихкод', 'id': 'product-barcode'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Описание', 'id': 'product-desc'}),
            'compatible_models': forms.SelectMultiple(attrs={'class': 'form-input', 'id': 'product-compatible', 'style': 'height:100px;'}),
            'analogs': forms.SelectMultiple(attrs={'class': 'form-input', 'id': 'product-analogs', 'style': 'height:100px;'}),
            'price_purchase': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00', 'step': '0.01', 'id': 'product-price-purchase'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0', 'id': 'product-stock'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0', 'id': 'product-minstock'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Полка / стеллаж', 'id': 'product-location'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox', 'id': 'product-active'}),
        }


class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories."""

    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название категории', 'id': 'category-name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Описание', 'id': 'category-desc'}),
        }


class PriceLevelForm(forms.ModelForm):
    """Form for creating/editing price markup levels."""

    class Meta:
        model = PriceLevel
        fields = ['name', 'markup_percent', 'order', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Напр: Розничная', 'id': 'level-name'}),
            'markup_percent': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '30', 'step': '0.01', 'id': 'level-markup'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '1', 'id': 'level-order'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox', 'id': 'level-default'}),
        }


class ImportForm(forms.Form):
    """Form for importing products from Excel/CSV."""
    file = forms.FileField(
        label='Файл (Excel или CSV)',
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.xlsx,.xls,.csv',
            'id': 'import-file',
        })
    )
