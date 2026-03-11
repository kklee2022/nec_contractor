from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from apps.core.permissions import AnyRoleRequiredMixin, ContractorRequiredMixin, PMRequiredMixin
from apps.projects.models import Project
from .models import DefinedCost, PaymentApplication
from .forms import DefinedCostForm, PaymentApplicationForm, PMAssessmentForm


class DefinedCostListView(AnyRoleRequiredMixin, ListView):
    model = DefinedCost
    template_name = 'financial/cost_list.html'
    context_object_name = 'costs'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return DefinedCost.objects.filter(project=self.project).select_related('entered_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        ctx['total'] = sum(c.amount for c in self.get_queryset())
        return ctx


class DefinedCostCreateView(ContractorRequiredMixin, CreateView):
    model = DefinedCost
    form_class = DefinedCostForm
    template_name = 'financial/cost_form.html'

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.get_project()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.entered_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Defined cost entry added.')
        return response

    def get_success_url(self):
        return reverse_lazy('financial:cost_list', kwargs={'project_pk': self.object.project.pk})


class PaymentApplicationListView(AnyRoleRequiredMixin, ListView):
    model = PaymentApplication
    template_name = 'financial/payment_list.html'
    context_object_name = 'applications'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return PaymentApplication.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        return ctx


class PaymentApplicationCreateView(ContractorRequiredMixin, CreateView):
    model = PaymentApplication
    form_class = PaymentApplicationForm
    template_name = 'financial/payment_form.html'

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.get_project()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.submitted_by = self.request.user
        form.instance.status = 'submitted'
        response = super().form_valid(form)
        messages.success(self.request, f'Payment Application #{self.object.application_number} submitted.')
        return response

    def get_success_url(self):
        return reverse_lazy('financial:payment_list', kwargs={'project_pk': self.object.project.pk})


class PMAssessmentView(PMRequiredMixin, UpdateView):
    model = PaymentApplication
    form_class = PMAssessmentForm
    template_name = 'financial/pm_assessment_form.html'

    def form_valid(self, form):
        form.instance.status = 'pm_assessed'
        response = super().form_valid(form)
        messages.success(self.request, 'Payment assessment saved.')
        return response

    def get_success_url(self):
        return reverse_lazy('financial:payment_list', kwargs={'project_pk': self.object.project.pk})
