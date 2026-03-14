from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='list'),
    path('new/', views.ProjectCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='update'),
    # Contract Data Part 1
    path('<int:pk>/contract-data/', views.contract_data_view, name='contract_data'),
    path('<int:pk>/contract-data/edit/', views.contract_data_edit, name='contract_data_edit'),
]
