from django.db import models
from apps.common import UUIDModel
from apps.accounts.models import User
from apps.events.models import Event, Subevent

class Registration(UUIDModel):
    STATUS = [('active', 'Ativa'), ('cancelled', 'Cancelada')]
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='registrations')
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    registered_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reactivated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'event'], name='unique_registration_per_event')]

class SubeventRegistration(UUIDModel):
    registration = models.ForeignKey(Registration, on_delete=models.PROTECT, related_name='subevent_registrations')
    subevent = models.ForeignKey(Subevent, on_delete=models.PROTECT, related_name='registrations')
    status = models.CharField(max_length=20, choices=Registration.STATUS, default='active')
    registered_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['registration', 'subevent'], name='unique_subevent_registration')]

class RegistrationHistory(UUIDModel):
    registration = models.ForeignKey(Registration, on_delete=models.PROTECT, related_name='history')
    subevent_registration = models.ForeignKey(SubeventRegistration, on_delete=models.PROTECT, null=True, blank=True, related_name='history')
    action = models.CharField(max_length=30)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
