"""
User forms: login, registration.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User


class LoginForm(AuthenticationForm):
    """Custom login form with styled widgets."""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите email',
            'id': 'login-email',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите пароль',
            'id': 'login-password',
            'autocomplete': 'current-password',
        })
    )


class RegisterForm(forms.ModelForm):
    """Registration form for new users."""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Мин. 8 символов',
            'id': 'register-password',
        })
    )
    password_confirm = forms.CharField(
        label='Подтвердите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Повторите пароль',
            'id': 'register-password-confirm',
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'company_name', 'phone', 'currency']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'email@company.com',
                'id': 'register-email',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Имя',
                'id': 'register-firstname',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Фамилия',
                'id': 'register-lastname',
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Название компании',
                'id': 'register-company',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+7 (___) ___-____',
                'id': 'register-phone',
            }),
            'currency': forms.Select(attrs={
                'class': 'form-input',
                'id': 'register-currency',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Пароли не совпадают')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'admin'  # First user is admin
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form to edit user profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'company_name', 'phone', 'currency']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'company_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'currency': forms.Select(attrs={'class': 'form-input'}),
        }
