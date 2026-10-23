# Controlled route registry: propose changes to Arya and API owner first.
from django.urls import path
from .api.csrf import csrf
from .api.login import LoginView
from .api.registration import RegistrationView
from .api.logout import LogoutView
from .api.me import MeView
urlpatterns = [path('csrf', csrf, name='csrf'), path('login', LoginView.as_view(), name='login'), path('register', RegistrationView.as_view(), name='register'), path('logout', LogoutView.as_view(), name='logout'), path('me', MeView.as_view(), name='me')]
