from django import forms
from .models import Organisation, OrganisationMembership
from apps.core.models import User


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ['name']


class MemberInviteForm(forms.Form):
    """Invite an existing registered user into the organisation."""
    email = forms.EmailField(
        label='User Email',
        help_text='Enter the email address of the registered user to invite.',
    )
    org_role = forms.ChoiceField(
        choices=OrganisationMembership.Role.choices,
        initial=OrganisationMembership.Role.MEMBER,
        label='Organisation Role',
    )
    nec_role = forms.ChoiceField(
        choices=User.Role.choices,
        label='NEC4 Role',
        help_text='The NEC4 contract role this person will fulfil.',
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            self._user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError(
                'No registered account found with this email address. '
                'The person must register first.'
            )
        return email

    def get_user(self):
        return getattr(self, '_user', None)


class MemberRoleForm(forms.ModelForm):
    """Change the org role of an existing member."""
    class Meta:
        model = OrganisationMembership
        fields = ['org_role']
        labels = {'org_role': 'Organisation Role'}
