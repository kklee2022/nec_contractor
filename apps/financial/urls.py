from django.urls import path
from . import views

app_name = 'financial'

urlpatterns = [
    path('project/<int:project_pk>/costs/', views.DefinedCostListView.as_view(), name='cost_list'),
    path('project/<int:project_pk>/costs/new/', views.DefinedCostCreateView.as_view(), name='cost_create'),
    path('project/<int:project_pk>/payments/', views.PaymentApplicationListView.as_view(), name='payment_list'),
    path('project/<int:project_pk>/payments/new/', views.PaymentApplicationCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/assess/', views.PMAssessmentView.as_view(), name='pm_assess'),
]
