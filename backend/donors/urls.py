from django.urls import path
from .api.search import DonorSearchView
from .api.profile import DonorProfileView
from .api.screening import ScreeningView
from .api.result import EligibilityResultView
urlpatterns = [path('donors', DonorSearchView.as_view(), name='search'), path('donors/<uuid:donor_id>', DonorProfileView.as_view(), name='profile'), path('donors/<uuid:donor_id>/eligibility', ScreeningView.as_view(), name='screening'), path('donors/<uuid:donor_id>/eligibility/result', EligibilityResultView.as_view(), name='result')]
