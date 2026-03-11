from django import forms
from .models import DefinedCost, PaymentApplication


class DefinedCostForm(forms.ModelForm):
    class Meta:
        model = DefinedCost
        fields = ['category', 'description', 'amount', 'currency', 'cost_date', 'receipt', 'linked_ce']
        widgets = {
            'cost_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class PaymentApplicationForm(forms.ModelForm):
    class Meta:
        model = PaymentApplication
        fields = ['application_number', 'period_from', 'period_to',
                  'gross_amount', 'retention', 'previous_certificates', 'net_amount']
        widgets = {
            'period_from': forms.DateInput(attrs={'type': 'date'}),
            'period_to': forms.DateInput(attrs={'type': 'date'}),
        }


class PMAssessmentForm(forms.ModelForm):
    class Meta:
        model = PaymentApplication
        fields = ['pm_assessed_amount', 'pm_assessment_date', 'pm_notes', 'payment_certificate']
        widgets = {
            'pm_assessment_date': forms.DateInput(attrs={'type': 'date'}),
            'pm_notes': forms.Textarea(attrs={'rows': 3}),
        }
