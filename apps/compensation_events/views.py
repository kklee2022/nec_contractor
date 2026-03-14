from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.db.models import Q
from apps.core.permissions import AnyRoleRequiredMixin, ContractorRequiredMixin
from apps.core.notifications import notify_ce_notified, notify_ce_state_changed
from apps.projects.models import Project
from .models import CompensationEvent
from .forms import CompensationEventForm, QuotationForm, PMReviewForm, ImplementForm


class CEListView(AnyRoleRequiredMixin, ListView):
    model = CompensationEvent
    template_name = 'compensation_events/ce_list.html'
    context_object_name = 'ces'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        qs = CompensationEvent.objects.filter(project=self.project).select_related('notified_by')
        q = self.request.GET.get('q', '').strip()
        state = self.request.GET.get('state', '').strip()
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(description__icontains=q))
        if state:
            qs = qs.filter(state=state)
        self._search = q
        self._state_filter = state
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        ctx['search'] = self._search
        ctx['state_filter'] = self._state_filter
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            from django.template.response import TemplateResponse
            return TemplateResponse(
                self.request,
                'compensation_events/_ce_table.html',
                context,
                **response_kwargs,
            )
        return super().render_to_response(context, **response_kwargs)


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
        ctx['state_steps'] = [
            {'key': 'notified',     'label': 'Notified',     'clause': 'Cl.60 / 61 — CE notified by Contractor'},
            {'key': 'quoted',       'label': 'Quoted',        'clause': 'Cl.62 — Contractor submits quotation (3 wks)'},
            {'key': 'pm_reviewing', 'label': 'PM Reviewing',  'clause': 'Cl.62.3 — PM reviews quotation'},
            {'key': 'implemented',  'label': 'Implemented',   'clause': 'Cl.65 — CE accepted & implemented'},
        ]
        state_order = [s['key'] for s in ctx['state_steps']]
        ctx['current_state_index'] = state_order.index(ce.state) if ce.state in state_order else -1
        return ctx


class CECreateView(ContractorRequiredMixin, CreateView):
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
        notify_ce_notified(self.object)
        return response

    def get_success_url(self):
        return reverse_lazy('compensation_events:list', kwargs={'project_pk': self.object.project.pk})


@login_required
def ce_submit_quotation(request, pk):
    """Contractor submits a quotation for a CE."""
    if request.user.role not in ('contractor', 'admin'):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('compensation_events:detail', pk=pk)
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            old_state = ce.state
            try:
                ce.submit_quotation(
                    cost=form.cleaned_data['quotation_cost'],
                    time_extension=form.cleaned_data['quotation_time_extension'],
                    detail=form.cleaned_data['quotation_detail'],
                    submitted_by=request.user,
                )
                ce.save()
                messages.success(request, f'Quotation submitted for {ce.reference}.')
                notify_ce_state_changed(ce, old_state)
            except Exception as e:
                messages.error(request, f'Cannot submit quotation: {e}')
    return redirect('compensation_events:detail', pk=pk)


@login_required
def ce_pm_review(request, pk):
    """Accept or reject a CE quotation (recorded from the contractor's perspective)."""
    if request.user.role not in ('contractor', 'admin'):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('compensation_events:detail', pk=pk)
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = PMReviewForm(request.POST)
        if form.is_valid():
            accepted = form.cleaned_data['accepted']
            reply = form.cleaned_data['pm_reply']
            ce.pm_reply = reply
            old_state = ce.state
            try:
                if accepted:
                    ce.pm_start_review()
                else:
                    ce.reject(reason=reply)
                ce.save()
                messages.success(request, f'CE {ce.reference} {"advanced" if accepted else "rejected"}.')
                notify_ce_state_changed(ce, old_state)
            except Exception as e:
                messages.error(request, f'Cannot update CE: {e}')
    return redirect('compensation_events:detail', pk=pk)


@login_required
def ce_implement(request, pk):
    """Mark a CE as implemented."""
    if request.user.role not in ('contractor', 'admin'):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('compensation_events:detail', pk=pk)
    ce = get_object_or_404(CompensationEvent, pk=pk)
    if request.method == 'POST':
        form = ImplementForm(request.POST)
        if form.is_valid():
            old_state = ce.state
            try:
                ce.implement(
                    cost=form.cleaned_data['implemented_cost'],
                    time_extension=form.cleaned_data['implemented_time_extension'],
                )
                ce.save()
                messages.success(request, f'CE {ce.reference} implemented.')
                notify_ce_state_changed(ce, old_state)
            except Exception as e:
                messages.error(request, f'Cannot implement CE: {e}')
    return redirect('compensation_events:detail', pk=pk)
