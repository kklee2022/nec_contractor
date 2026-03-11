from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Organisation dashboard
    path('organisation/', views.org_dashboard, name='org_dashboard'),

    # Member management
    path('organisation/members/', views.member_list, name='member_list'),
    path('organisation/members/invite/', views.member_invite, name='member_invite'),
    path('organisation/members/<int:pk>/role/', views.member_role_change, name='member_role_change'),
    path('organisation/members/<int:pk>/remove/', views.member_remove, name='member_remove'),

    # Billing
    path('organisation/billing/', views.billing, name='billing'),
    path('organisation/billing/success/', views.billing_success, name='billing_success'),
    path('organisation/billing/checkout/', views.create_checkout_session, name='create_checkout_session'),
    path('organisation/billing/portal/', views.billing_portal, name='billing_portal'),

    # Stripe webhook (no auth)
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
