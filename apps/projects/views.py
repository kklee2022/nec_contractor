from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.core.permissions import AnyRoleRequiredMixin, PMRequiredMixin, PlanLimitMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Project, Programme, ContractData
from .forms import (
    ProjectForm, ProgrammeForm,
    ContractDataForm, SiteAccessDateFormSet, ContractSectionFormSet,
)


class ProjectListView(AnyRoleRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'

    def get(self, request, *args, **kwargs):
        """Singleton redirect: go straight to the project or to create."""
        qs = self._base_queryset(request)
        if qs.count() == 1:
            return redirect('projects:detail', pk=qs.first().pk)
        if qs.count() == 0:
            return redirect('projects:create')
        return super().get(request, *args, **kwargs)

    def _base_queryset(self, request):
        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(request.user)
        if org:
            return Project.objects.filter(organisation=org).select_related(
                'contractor', 'contractor_representative'
            )
        return Project.objects.filter(members=request.user).select_related(
            'contractor', 'contractor_representative'
        )

    def get_queryset(self):
        return self._base_queryset(self.request)


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

    def get(self, request, *args, **kwargs):
        """Redirect to edit if a project already exists (singleton)."""
        existing = Project.objects.first()
        if existing:
            messages.info(request, 'A project already exists. Edit it below.')
            return redirect('projects:update', pk=existing.pk)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(self.request.user)
        if org:
            form.instance.organisation = org
        response = super().form_valid(form)
        project = self.object
        # Auto-add the Contractor's Representative as a project member
        if project.contractor_representative:
            project.members.add(project.contractor_representative)
        messages.success(self.request, f'Project "{project}" created successfully.')
        return response


class ProjectUpdateView(PMRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:detail', kwargs={'pk': self.object.pk})


# ─── Contract Data views ───────────────────────────────────────────────────────

@login_required
def contract_data_view(request, pk):
    """Read-only display of Contract Data Part 1."""
    project = get_object_or_404(Project, pk=pk)
    cd = getattr(project, 'contract_data', None)
    return render(request, 'projects/contract_data.html', {
        'project': project,
        'cd': cd,
    })


@login_required
def contract_data_edit(request, pk):
    """Create or update Contract Data Part 1, including inline formsets."""
    project = get_object_or_404(Project, pk=pk)
    if not (request.user.is_contractor or request.user.is_admin_user):
        messages.error(request, 'Only Contractor staff or an Administrator can edit Contract Data.')
        return redirect('projects:contract_data', pk=pk)

    cd, _ = ContractData.objects.get_or_create(project=project)

    if request.method == 'POST':
        form       = ContractDataForm(request.POST, instance=cd)
        access_fs  = SiteAccessDateFormSet(request.POST, instance=cd, prefix='access')
        section_fs = ContractSectionFormSet(request.POST, instance=cd, prefix='sections')
        if form.is_valid() and access_fs.is_valid() and section_fs.is_valid():
            form.save()
            access_fs.save()
            section_fs.save()
            messages.success(request, 'Contract Data saved successfully.')
            return redirect('projects:contract_data', pk=pk)
    else:
        form       = ContractDataForm(instance=cd)
        access_fs  = SiteAccessDateFormSet(instance=cd, prefix='access')
        section_fs = ContractSectionFormSet(instance=cd, prefix='sections')

    return render(request, 'projects/contract_data_form.html', {
        'project':    project,
        'cd':         cd,
        'form':       form,
        'access_fs':  access_fs,
        'section_fs': section_fs,
    })
