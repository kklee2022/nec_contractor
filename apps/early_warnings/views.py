from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from apps.core.permissions import AnyRoleRequiredMixin, ContractorRequiredMixin
from apps.core.notifications import notify_ew_raised, notify_ew_status_changed
from apps.projects.models import Project
from .models import EarlyWarning
from .forms import EarlyWarningForm, EarlyWarningUpdateForm


class EarlyWarningListView(AnyRoleRequiredMixin, ListView):
    model = EarlyWarning
    template_name = 'early_warnings/ew_list.html'
    context_object_name = 'early_warnings'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        qs = EarlyWarning.objects.filter(project=self.project).select_related('raised_by')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        self._search = q
        self._status_filter = status
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        ctx['search'] = getattr(self, '_search', '')
        ctx['status_filter'] = getattr(self, '_status_filter', '')
        return ctx

    def render_to_response(self, context, **kwargs):
        if self.request.htmx:
            return render(self.request, 'early_warnings/_ew_table.html', context)
        return super().render_to_response(context, **kwargs)


class EarlyWarningDetailView(AnyRoleRequiredMixin, DetailView):
    model = EarlyWarning
    template_name = 'early_warnings/ew_detail.html'
    context_object_name = 'ew'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['update_form'] = EarlyWarningUpdateForm(instance=self.object)
        return ctx


class EarlyWarningCreateView(ContractorRequiredMixin, CreateView):
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
        notify_ew_raised(self.object)
        return response

    def get_success_url(self):
        return reverse_lazy('early_warnings:list', kwargs={'project_pk': self.object.project.pk})


class EarlyWarningUpdateView(ContractorRequiredMixin, UpdateView):
    model = EarlyWarning
    form_class = EarlyWarningUpdateForm
    template_name = 'early_warnings/ew_form.html'

    def form_valid(self, form):
        # Capture old status before save so the notification shows the change
        old_status = EarlyWarning.objects.get(pk=form.instance.pk).status
        if form.instance.status in ['actioned', 'closed'] and not form.instance.resolved_by:
            form.instance.resolved_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Early Warning {self.object.reference} updated.')
        if self.object.status != old_status:
            notify_ew_status_changed(self.object, old_status)
        return response

    def get_success_url(self):
        return reverse_lazy('early_warnings:detail', kwargs={'pk': self.object.pk})
