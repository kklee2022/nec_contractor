from django import forms
from .models import CompensationEvent


class CompensationEventForm(forms.ModelForm):
    class Meta:
        model = CompensationEvent
        fields = ['clause', 'description', 'notification_date']
        widgets = {
            'notification_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class QuotationForm(forms.Form):
    quotation_cost = forms.DecimalField(max_digits=14, decimal_places=2, label='Quoted Cost (£)')
    quotation_time_extension = forms.IntegerField(
        min_value=0, label='Time Extension (days)',
        help_text='Enter 0 if no time extension is claimed'
    )
    quotation_detail = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label='Quotation Detail')


class PMReviewForm(forms.Form):
    accepted = forms.BooleanField(required=False, label='Accept CE?')
    pm_reply = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='PM Response / Reason')


class ImplementForm(forms.Form):
    implemented_cost = forms.DecimalField(max_digits=14, decimal_places=2, label='Final Cost (£)')
    implemented_time_extension = forms.IntegerField(min_value=0, label='Agreed Time Extension (days)')
