import uuid
from django.db import models
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and (request.user.role == 'admin'))

class IsOrganizerOrAdmin(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and (request.user.role in ('organizer', 'admin')))

def ensure(condition, message):
    if not condition:
        raise PermissionDenied(message)
