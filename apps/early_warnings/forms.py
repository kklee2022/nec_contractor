from django import forms
from .models import EarlyWarning, EarlyWarningAttachment


class EarlyWarningForm(forms.ModelForm):
    class Meta:
        model = EarlyWarning
        fields = ['description', 'potential_impact', 'mitigation', 'raised_by_party']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'potential_impact': forms.Textarea(attrs={'rows': 3}),
            'mitigation': forms.Textarea(attrs={'rows': 3}),
        }


class EarlyWarningUpdateForm(forms.ModelForm):
    class Meta:
        model = EarlyWarning
        fields = ['status', 'mitigation', 'risk_reduction_meeting_date',
                  'risk_reduction_meeting_notes', 'resolved_date']
        widgets = {
            'risk_reduction_meeting_date': forms.DateInput(attrs={'type': 'date'}),
            'resolved_date': forms.DateInput(attrs={'type': 'date'}),
            'mitigation': forms.Textarea(attrs={'rows': 3}),
            'risk_reduction_meeting_notes': forms.Textarea(attrs={'rows': 3}),
        }
