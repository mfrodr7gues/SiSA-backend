from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from apps.common import UUIDModel
from apps.accounts.models import User

class Event(UUIDModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    registration_opens_at = models.DateTimeField()
    registration_closes_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    cover = models.ImageField(upload_to='events/')
    organizer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='organized_events')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_events')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')), name='event_dates_valid'), models.CheckConstraint(condition=Q(registration_opens_at__lt=F('registration_closes_at')), name='event_registration_dates_valid'), models.CheckConstraint(condition=Q(capacity__gt=0), name='event_capacity_positive')]

    @property
    def status(self):
        now = timezone.now()
        if self.cancelled_at:
            return 'cancelled'
        if now >= self.ends_at:
            return 'finished'
        if now >= self.starts_at:
            return 'in_progress'
        if self.registration_opens_at <= now < self.registration_closes_at:
            return 'registration_open'
        return 'upcoming'

    def __str__(self):
        return self.title

class Subevent(UUIDModel):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='subevents')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    cover = models.ImageField(upload_to='subevents/', blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')), name='subevent_dates_valid'), models.CheckConstraint(condition=Q(capacity__gt=0), name='subevent_capacity_positive')]

class EventSession(UUIDModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=150, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['starts_at']
        constraints = [models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')), name='event_session_dates_valid')]

class SubeventSession(UUIDModel):
    subevent = models.ForeignKey(Subevent, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=150, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['starts_at']
        constraints = [models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')), name='subevent_session_dates_valid')]
