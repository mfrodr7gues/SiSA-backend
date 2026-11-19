from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegistrationViewSet, SubeventRegistrationViewSet
r = DefaultRouter()
r.register('registrations', RegistrationViewSet, basename='registration')
r.register('subevent-registrations', SubeventRegistrationViewSet, basename='subevent-registration')
urlpatterns = [path('', include(r.urls))]
