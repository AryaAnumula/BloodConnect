from django.urls import include, path
from django.views.generic import TemplateView
from core.health import live, ready
urlpatterns = [
    path('api/v1/health/live', live, name='live'),
    path('api/v1/health/ready', ready, name='ready'),
    path('api/v1/auth/', include(('accounts.urls', 'accounts'))),
    path('api/v1/', include(('donors.urls', 'donors'))),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('login', TemplateView.as_view(template_name='login.html'), name='login-page'),
    path('register', TemplateView.as_view(template_name='register.html'), name='register-page'),
    path('screening', TemplateView.as_view(template_name='screening.html'), name='screening-page'),
    path('eligibility', TemplateView.as_view(template_name='eligibility.html'), name='result-page'),
    path('staff/donors', TemplateView.as_view(template_name='search.html'), name='search-page'),
]
