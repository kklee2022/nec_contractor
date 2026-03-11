from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from apps.core.permissions import AnyRoleRequiredMixin, PMOrContractorRequiredMixin
from apps.projects.models import Project
from .models import EarlyWarning
from .forms import EarlyWarningForm, EarlyWarningUpdateForm


class EarlyWarningListView(AnyRoleRequiredMixin, ListView):
    model = EarlyWarning
    template_name = 'early_warnings/ew_list.html'
    context_object_name = 'early_warnings'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return EarlyWarning.objects.filter(project=self.project).select_related('raised_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        return ctx


class EarlyWarningDetailView(AnyRoleRequiredMixin, DetailView):
    model = EarlyWarning
    template_name = 'early_warnings/ew_detail.html'
    context_object_name = 'ew'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['update_form'] = EarlyWarningUpdateForm(instance=self.object)
        return ctx


class EarlyWarningCreateView(PMOrContractorRequiredMixin, CreateView):
    model = EarlyWarning
    form_class = EarlyWarningForm
    template_name = 'early_warnings/ew_form.html'

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.get_project()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.raised_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Early Warning {self.object.reference} raised successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy('early_warnings:list', kwargs={'project_pk': self.object.project.pk})


class EarlyWarningUpdateView(PMOrContractorRequiredMixin, UpdateView):
    model = EarlyWarning
    form_class = EarlyWarningUpdateForm
    template_name = 'early_warnings/ew_form.html'

    def form_valid(self, form):
        if form.instance.status in ['actioned', 'closed'] and not form.instance.resolved_by:
            form.instance.resolved_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Early Warning {self.object.reference} updated.')
        return response

    def get_success_url(self):
        return reverse_lazy('early_warnings:detail', kwargs={'pk': self.object.pk})
