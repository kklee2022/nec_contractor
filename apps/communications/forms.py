from django import forms
from .models import Communication


class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        fields = ['communication_type', 'direction', 'subject', 'body', 'sent_date',
                  'linked_ce', 'linked_ew', 'attachment']
        widgets = {
            'sent_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'body': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['linked_ce'].queryset = project.compensation_events.all()
            self.fields['linked_ew'].queryset = project.early_warnings.all()
