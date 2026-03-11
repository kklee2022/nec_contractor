from django.urls import path
from . import views

app_name = 'early_warnings'

urlpatterns = [
    path('project/<int:project_pk>/', views.EarlyWarningListView.as_view(), name='list'),
    path('project/<int:project_pk>/new/', views.EarlyWarningCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EarlyWarningDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.EarlyWarningUpdateView.as_view(), name='update'),
]
