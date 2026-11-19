from django.db import models
from apps.common import UUIDModel
from apps.accounts.models import User
from apps.registrations.models import Registration, SubeventRegistration

class EventAttendance(UUIDModel):
    registration = models.OneToOneField(Registration, on_delete=models.PROTECT, related_name='attendance')
    present = models.BooleanField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SubeventAttendance(UUIDModel):
    subevent_registration = models.OneToOneField(SubeventRegistration, on_delete=models.PROTECT, related_name='attendance')
    present = models.BooleanField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
