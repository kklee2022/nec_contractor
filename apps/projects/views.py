from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.core.permissions import AnyRoleRequiredMixin, PMRequiredMixin, PlanLimitMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Project, Programme
from .forms import ProjectForm, ProgrammeForm


class ProjectListView(AnyRoleRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(self.request.user)
        if org:
            return Project.objects.filter(organisation=org).select_related(
                'contractor', 'project_manager'
            )
        return Project.objects.filter(members=self.request.user).select_related(
            'contractor', 'project_manager'
        )


class ProjectDetailView(AnyRoleRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_object(self):
        obj = get_object_or_404(Project, pk=self.kwargs['pk'])
        # Ensure user is a member or org admin
        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(self.request.user)
        user_in_org = org and obj.organisation == org
        if not user_in_org and self.request.user not in obj.members.all() and not self.request.user.is_admin_user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        ctx['early_warnings'] = project.early_warnings.order_by('-created_at')[:5]
        ctx['compensation_events'] = project.compensation_events.order_by('-created_at')[:5]
        ctx['programmes'] = project.programmes.order_by('-revision')[:3]
        return ctx


class ProjectCreateView(PlanLimitMixin, PMRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:list')
    limit_check = 'project'

    def form_valid(self, form):
        # Assign to user's organisation
        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(self.request.user)
        if org:
            form.instance.organisation = org
        response = super().form_valid(form)
        # Auto-add key parties as members
        project = self.object
        project.members.add(project.contractor, project.project_manager)
        if project.supervisor:
            project.members.add(project.supervisor)
        messages.success(self.request, f'Project "{project}" created successfully.')
        return response


class ProjectUpdateView(PMRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:detail', kwargs={'pk': self.object.pk})
