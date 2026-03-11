from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from apps.core.permissions import AnyRoleRequiredMixin, PMOrContractorRequiredMixin
from apps.projects.models import Project
from .models import Communication
from .forms import CommunicationForm


class CommunicationListView(AnyRoleRequiredMixin, ListView):
    model = Communication
    template_name = 'communications/comm_list.html'
    context_object_name = 'communications'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return Communication.objects.filter(project=self.project).select_related('sent_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.project
        return ctx


class CommunicationCreateView(PMOrContractorRequiredMixin, CreateView):
    model = Communication
    form_class = CommunicationForm
    template_name = 'communications/comm_form.html'

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.get_project()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.get_project()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.sent_by = self.request.user
        try:
            form.instance.full_clean()
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        response = super().form_valid(form)
        messages.success(self.request, f'Communication {self.object.reference} logged.')
        return response

    def get_success_url(self):
        return reverse_lazy('communications:list', kwargs={'project_pk': self.object.project.pk})


def acknowledge_communication(request, pk):
    comm = get_object_or_404(Communication, pk=pk)
    if request.method == 'POST':
        comm.acknowledged = True
        comm.acknowledged_by = request.user
        comm.acknowledged_date = timezone.now()
        comm.save()
        messages.success(request, f'{comm.reference} acknowledged.')
    return redirect('communications:list', project_pk=comm.project.pk)
