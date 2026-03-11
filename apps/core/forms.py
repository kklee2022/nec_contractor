from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegistrationForm(UserCreationForm):
    """Public self-registration form — creates account + new Organisation."""
    organisation_name = forms.CharField(
        max_length=255,
        label='Organisation / Company Name',
        help_text='This will be the name of your account on the platform.',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'organisation_name', 'organisation', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        # 'organisation' here is the legacy CharField — relabel it
        self.fields['organisation'].label = 'Company / Firm'
        self.fields['organisation'].required = False
        self.fields['organisation'].help_text = 'Your company or firm name (optional display field).'


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'organisation', 'phone', 'avatar']


# ─── People CRUD (admin-managed users) ────────────────────────────────────────

class PersonForm(forms.ModelForm):
    """Create or edit a Contractor, Project Manager, or Supervisor."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Enter password'}),
        required=False,
        help_text='Leave blank to keep the existing password. Required when creating a new user.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Confirm password'}),
        required=False,
        label='Confirm Password',
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'role', 'organisation', 'phone', 'is_active',
        ]
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        self.is_new = kwargs.get('instance') is None
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        if self.is_new:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
            self.fields['is_active'].initial = True
        # Limit role choices to non-admin roles
        self.fields['role'].choices = [
            c for c in User.Role.choices if c[0] != User.Role.ADMIN
        ]

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw or cpw:
            if pw != cpw:
                self.add_error('confirm_password', 'Passwords do not match.')
        if self.is_new and not pw:
            self.add_error('password', 'Password is required for new users.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('password')
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user
