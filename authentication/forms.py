"""
Authentication forms for login, registration, and user management.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from apps.models import User, School, UserApplication


class LoginForm(forms.Form):
    """
    Custom login form with school selection for multi-tenant support.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Enter your username',
            'autofocus': True,
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Enter your password',
            'required': True
        })
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
        empty_label="Select school (optional for admin)",
        widget=forms.Select(attrs={
            'class': 'form-control form-control-modern'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class RegistrationForm(forms.ModelForm):
    """
    Form for user registration with email and password confirmation.
    """
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Enter password',
            'required': True
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Confirm password',
            'required': True
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'school', 'role']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Username',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Email',
                'required': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'First Name',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Last Name',
                'required': True
            }),
            'school': forms.Select(attrs={
                'class': 'form-control form-control-modern',
                'required': True
            }),
            'role': forms.Select(attrs={
                'class': 'form-control form-control-modern',
                'required': True
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserApplicationForm(forms.ModelForm):
    """
    Form for user applications requiring admin approval.
    """
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Enter password',
            'required': True
        })
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-modern',
            'placeholder': 'Confirm password',
            'required': True
        })
    )

    class Meta:
        model = UserApplication
        fields = ['username', 'email', 'first_name', 'last_name', 'school', 'role']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Username',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Email',
                'required': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'First Name',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Last Name',
                'required': True
            }),
            'school': forms.Select(attrs={
                'class': 'form-control form-control-modern',
                'required': True
            }),
            'role': forms.Select(attrs={
                'class': 'form-control form-control-modern',
                'required': True
            }),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return password_confirm

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        if UserApplication.objects.filter(username=username, status='pending').exists():
            raise forms.ValidationError('Application already pending for this username.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email
