from django import forms
from django.forms import inlineformset_factory
from apps.core.models import User, ContractorOrganisation
from .models import Project, Programme, ContractData, SiteAccessDate, ContractSection


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'reference', 'description', 'status',
            # PM (external company)
            'pm_company', 'pm_representative', 'pm_contact_email',
            # Supervisor (external company)
            'supervisor_company', 'supervisor_representative', 'supervisor_contact_email',
            # Contractor (system user + company)
            'contractor_representative', 'contractor',
            # Dates & financials
            'start_date', 'completion_date', 'contract_sum',
            # Reference prefixes
            'ce_reference_prefix', 'ew_reference_prefix',
        ]
        widgets = {
            'start_date':      forms.DateInput(attrs={'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description':     forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'pm_company':               'Company Name',
            'pm_representative':        'Named Representative',
            'pm_contact_email':         'Contact Email',
            'supervisor_company':       'Company Name',
            'supervisor_representative':'Named Representative',
            'supervisor_contact_email': 'Contact Email',
            'contractor_representative':'Contractor (Named Representative)',
            'contractor':               'Contractor Company (optional)',
        }
        help_texts = {
            'pm_company':               'NEC4 Cl.14.2 — The company appointed as Project Manager.',
            'supervisor_company':       'NEC4 Cl.14.4 — The company appointed as Supervisor.',
            'contractor_representative': 'NEC4 Cl.11.2(6) — Select from registered Contractor staff.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contractor'].queryset = ContractorOrganisation.objects.all()
        self.fields['contractor'].required = False
        self.fields['contractor_representative'].queryset = User.objects.filter(
            role=User.Role.CONTRACTOR, is_active=True
        )
        self.fields['contractor_representative'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('pm_company'):
            self.add_error('pm_company', 'Project Manager company must be named (NEC4 Cl.14.2).')
        if not cleaned_data.get('pm_representative'):
            self.add_error('pm_representative', "PM's named representative is required.")
        if not cleaned_data.get('supervisor_company'):
            self.add_error('supervisor_company', 'Supervisor company must be named (NEC4 Cl.14.4).')
        if not cleaned_data.get('supervisor_representative'):
            self.add_error('supervisor_representative', "Supervisor's named representative is required.")
        if not cleaned_data.get('contractor_representative'):
            self.add_error('contractor_representative', 'A Contractor must be selected (NEC4 Cl.11.2(6)).')
        return cleaned_data


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ['revision', 'programme_file', 'notes']


# ─── Contract Data ─────────────────────────────────────────────────────────────

_TA = lambda r: forms.Textarea(attrs={'rows': r, 'class': 'form-control'})
_DI = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})


class ContractDataForm(forms.ModelForm):
    """Main form for Contract Data Part 1 (all sections except inline formsets)."""

    class Meta:
        model = ContractData
        exclude = ['project']
        widgets = {
            # General
            'works_description':          _TA(3),
            'adjudicator':                _TA(2),
            # Time
            'contract_date':              _DI,
            'starting_date':              _DI,
            'completion_date':            _DI,
            'risk_register_items':        _TA(6),
            # Payment / Insurance / Options
            'interest_rate':              _TA(3),
            'insurance_notes':            _TA(4),
            'method_of_measurement':      _TA(3),
            'advance_payment_amount':     _TA(2),
            'advance_payment_repayment':  _TA(2),
            'additional_conditions_notes': _TA(3),
        }


class SiteAccessDateForm(forms.ModelForm):
    """Single row in the Site Access Dates inline formset."""

    class Meta:
        model = SiteAccessDate
        fields = ['site_portion', 'access_description', 'access_date', 'conditions']
        widgets = {
            'site_portion':       forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'access_description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'access_date':        forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'conditions':         forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }


SiteAccessDateFormSet = inlineformset_factory(
    ContractData, SiteAccessDate,
    form=SiteAccessDateForm,
    extra=1, can_delete=True,
)


class ContractSectionForm(forms.ModelForm):
    """Single row in the Contract Sections inline formset (X5/X7)."""

    class Meta:
        model = ContractSection
        fields = [
            'section_number', 'description', 'completion_days', 'completion_date',
            'delay_damages_per_day', 'delay_damages_formula', 'min_delay_damages',
        ]
        widgets = {
            'section_number':        forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'description':           forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'completion_days':       forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'completion_date':       forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'delay_damages_per_day': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'delay_damages_formula': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'min_delay_damages':     forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }


ContractSectionFormSet = inlineformset_factory(
    ContractData, ContractSection,
    form=ContractSectionForm,
    extra=1, can_delete=True,
)
