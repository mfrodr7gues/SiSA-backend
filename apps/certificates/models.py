import secrets
from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from apps.common import UUIDModel
from apps.attendance.models import EventAttendance, SubeventAttendance

def make_code():
    return secrets.token_urlsafe(24)
private_certificate_storage = FileSystemStorage(location=settings.BASE_DIR / 'private_certificates')

class Certificate(UUIDModel):
    event_attendance = models.OneToOneField(EventAttendance, on_delete=models.PROTECT, null=True, blank=True, related_name='certificate')
    subevent_attendance = models.OneToOneField(SubeventAttendance, on_delete=models.PROTECT, null=True, blank=True, related_name='certificate')
    code = models.CharField(max_length=100, unique=True, default=make_code)
    participant_name = models.CharField(max_length=200)
    activity_name = models.CharField(max_length=200)
    workload_minutes = models.PositiveIntegerField()
    activity_starts_at = models.DateTimeField()
    activity_ends_at = models.DateTimeField()
    institution = models.CharField(max_length=200, default='Instituto Federal do Ceará — Campus Cedro')
    pdf = models.FileField(upload_to='certificates/', storage=private_certificate_storage, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(event_attendance__isnull=False, subevent_attendance__isnull=True) | Q(event_attendance__isnull=True, subevent_attendance__isnull=False), name='certificate_one_attendance')]
