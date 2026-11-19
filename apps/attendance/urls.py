from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventAttendanceViewSet, SubeventAttendanceViewSet, AttendanceSheetViewSet
r = DefaultRouter()
r.register('event-attendance', EventAttendanceViewSet, basename='event-attendance')
r.register('subevent-attendance', SubeventAttendanceViewSet, basename='subevent-attendance')
r.register('attendance-sheets', AttendanceSheetViewSet, basename='attendance-sheets')
urlpatterns = [path('', include(r.urls))]
