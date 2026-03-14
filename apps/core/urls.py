from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard & Profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # Public registration (mounted at /accounts/register/)
    path('accounts/register/', views.register_view, name='register'),

    # People CRUD (admin only) — generic
    path('people/', views.people_list_view, name='people_list'),
    path('people/new/', views.person_create_view, name='person_create'),
    path('people/<int:pk>/edit/', views.person_edit_view, name='person_edit'),
    path('people/<int:pk>/deactivate/', views.person_deactivate_view, name='person_deactivate'),

    # People CRUD — role-specific (contractors / project-managers / supervisors)
    path('people/<slug:role_slug>/', views.role_person_list, name='role_person_list'),
    path('people/<slug:role_slug>/new/', views.role_person_create, name='role_person_create'),
    path('people/<slug:role_slug>/<int:pk>/edit/', views.role_person_edit, name='role_person_edit'),
    path('people/<slug:role_slug>/<int:pk>/deactivate/', views.role_person_deactivate, name='role_person_deactivate'),

    # Contractor Organisation (the company entity)
    path('contractor/', views.contractor_org_detail, name='contractor_org_detail'),
    path('contractor/new/', views.contractor_org_create, name='contractor_org_create'),
    path('contractor/edit/', views.contractor_org_edit, name='contractor_org_edit'),
]
