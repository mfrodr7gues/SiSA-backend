from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, SubeventViewSet, EventSessionViewSet, SubeventSessionViewSet
r = DefaultRouter()
r.register('events', EventViewSet)
r.register('subevents', SubeventViewSet)
r.register('event-sessions', EventSessionViewSet, basename='event-session')
r.register('subevent-sessions', SubeventSessionViewSet, basename='subevent-session')
urlpatterns = [path('', include(r.urls))]
