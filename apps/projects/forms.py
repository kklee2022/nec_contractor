from django import forms
from .models import Project, Programme


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'reference', 'description', 'status',
            'contractor', 'project_manager', 'supervisor',
            'start_date', 'completion_date', 'contract_sum',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ['revision', 'programme_file', 'notes']
