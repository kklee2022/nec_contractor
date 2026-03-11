from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard & Profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # Public registration (mounted at /accounts/register/)
    path('accounts/register/', views.register_view, name='register'),

    # People CRUD (admin only)
    path('people/', views.people_list_view, name='people_list'),
    path('people/new/', views.person_create_view, name='person_create'),
    path('people/<int:pk>/edit/', views.person_edit_view, name='person_edit'),
    path('people/<int:pk>/deactivate/', views.person_deactivate_view, name='person_deactivate'),
]
