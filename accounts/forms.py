from django import forms
from django.contrib.auth.models import User
from core.models import College


class SignupForm(forms.Form):
    """Registration form with college selection."""
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name',
            'id': 'signup-first-name',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name',
            'id': 'signup-last-name',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@college.edu',
            'id': 'signup-email',
            'autocomplete': 'email',
        })
    )
    college = forms.ModelChoiceField(
        queryset=College.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'id': 'signup-college',
        }),
        empty_label='Choose your college...',
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Min 8 characters',
            'id': 'signup-password',
            'autocomplete': 'new-password',
        })
    )
    confirm_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
            'id': 'signup-confirm-password',
            'autocomplete': 'new-password',
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class LoginForm(forms.Form):
    """Login form."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@college.edu',
            'id': 'login-email',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'id': 'login-password',
            'autocomplete': 'current-password',
        })
    )
