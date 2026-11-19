from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificateViewSet, CertificateVerifyViewSet
r = DefaultRouter()
r.register('certificates', CertificateViewSet, basename='certificate')
urlpatterns = [path('certificates/verify/<str:pk>/', CertificateVerifyViewSet.as_view({'get': 'retrieve'})), path('', include(r.urls))]
