from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name='register'),
    path("login/", LoginView.as_view(), name='login'),
    path("predict/", predict_damage, name="predict_damage"),
    path("token/", TokenVerifyView.as_view(), name='token_verify_view'),
    path("token/refresh/", TokenRefreshView.as_view(), name='token_refresh'),
    path("registrations/create/", RegistrationCreateView.as_view(), name='registration_create'),
    path("registrations/list/", RegistrationListView.as_view(), name='registration_list'),
    path("contact/create/", ContactFormCreateView.as_view(), name='contact_create'),
    path("contact/list/", ContactFormListView.as_view(), name='contact_list'),
    path("company/all/", ManufacturerDataListView.as_view(), name='manufacturer_list'),
]
