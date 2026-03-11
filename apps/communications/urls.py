from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('project/<int:project_pk>/', views.CommunicationListView.as_view(), name='list'),
    path('project/<int:project_pk>/new/', views.CommunicationCreateView.as_view(), name='create'),
    path('<int:pk>/acknowledge/', views.acknowledge_communication, name='acknowledge'),
]
