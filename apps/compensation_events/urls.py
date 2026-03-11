from django.urls import path
from . import views

app_name = 'compensation_events'

urlpatterns = [
    path('project/<int:project_pk>/', views.CEListView.as_view(), name='list'),
    path('project/<int:project_pk>/new/', views.CECreateView.as_view(), name='create'),
    path('<int:pk>/', views.CEDetailView.as_view(), name='detail'),
    path('<int:pk>/quotation/', views.ce_submit_quotation, name='submit_quotation'),
    path('<int:pk>/pm-review/', views.ce_pm_review, name='pm_review'),
    path('<int:pk>/implement/', views.ce_implement, name='implement'),
]
