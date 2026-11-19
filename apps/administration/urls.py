from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserViewSet, OrganizerRequestViewSet, OrganizerReassignmentView, DashboardView, AuditViewSet
r = DefaultRouter()
r.register('admin/users', AdminUserViewSet, basename='admin-user')
r.register('admin/organizer-requests', OrganizerRequestViewSet, basename='organizer-request')
r.register('admin/audit-logs', AuditViewSet, basename='audit-log')
urlpatterns = [path('admin/events/<uuid:pk>/organizer/', OrganizerReassignmentView.as_view()), path('admin/dashboard/', DashboardView.as_view()), path('', include(r.urls))]
