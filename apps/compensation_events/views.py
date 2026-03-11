from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from apps.core.permissions import AnyRoleRequiredMixin, PMOrContractorRequiredMixin, PMRequiredMixin, ContractorRequiredMixin
from apps.projects.models import Project
from .models import CompensationEvent
from .forms import CompensationEventForm, QuotationForm, PMReviewForm, ImplementForm


class CEListView(AnyRoleRequiredMixin, ListView):
    model = CompensationEvent
    template_name = 'compensation_events/ce_list.html'
    context_object_name = 'ces'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return CompensationEvent.objects.filter(project=self.project).select_related('notified_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        return ctx


class CEDetailView(AnyRoleRequiredMixin, DetailView):
    model = CompensationEvent
    template_name = 'compensation_events/ce_detail.html'
    context_object_name = 'ce'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ce = self.object
        ctx['quotation_form'] = QuotationForm()
        ctx['pm_review_form'] = PMReviewForm()
        ctx['implement_form'] = ImplementForm()
        return ctx


class CECreateView(PMOrContractorRequiredMixin, CreateView):
    model = CompensationEvent
    form_class = CompensationEventForm
    template_name = 'compensation_events/ce_form.html'

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.get_project()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.notified_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Compensation Event {self.object.reference} notified.')
        return response

    def get_success_url(self):
        return reverse_lazy('compensation_events:list', kwargs={'project_pk': self.object.project.pk})


def ce_submit_quotation(request, pk):
    """Contractor submits a quotation for a CE."""
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            try:
                ce.submit_quotation(
                    cost=form.cleaned_data['quotation_cost'],
                    time_extension=form.cleaned_data['quotation_time_extension'],
                    detail=form.cleaned_data['quotation_detail'],
                    submitted_by=request.user,
                )
                ce.save()
                messages.success(request, f'Quotation submitted for {ce.reference}.')
            except Exception as e:
                messages.error(request, f'Cannot submit quotation: {e}')
    return redirect('compensation_events:detail', pk=pk)


def ce_pm_review(request, pk):
    """PM accepts or rejects a CE quotation."""
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = PMReviewForm(request.POST)
        if form.is_valid():
            accepted = form.cleaned_data['accepted']
            reply = form.cleaned_data['pm_reply']
            ce.pm_reply = reply
            try:
                if accepted:
                    ce.pm_start_review()
                else:
                    ce.reject(reason=reply)
                ce.save()
                messages.success(request, f'CE {ce.reference} {"advanced" if accepted else "rejected"}.')
            except Exception as e:
                messages.error(request, f'Cannot update CE: {e}')
    return redirect('compensation_events:detail', pk=pk)


def ce_implement(request, pk):
    """Mark a CE as implemented."""
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = ImplementForm(request.POST)
        if form.is_valid():
            try:
                ce.implement(
                    cost=form.cleaned_data['implemented_cost'],
                    time_extension=form.cleaned_data['implemented_time_extension'],
                )
                ce.save()
                messages.success(request, f'CE {ce.reference} implemented.')
            except Exception as e:
                messages.error(request, f'Cannot implement CE: {e}')
    return redirect('compensation_events:detail', pk=pk)
