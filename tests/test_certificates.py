from datetime import timedelta
import pytest
from django.utils import timezone
from apps.accounts.models import User
from apps.events.models import Event, EventSession
from apps.registrations.models import Registration
from apps.attendance.models import EventAttendance
from apps.certificates.models import Certificate
from apps.certificates.services import issue_pending

@pytest.mark.django_db
def test_certificate_issued_once_for_present_attendee(settings, tmp_path):
    from apps.certificates.models import private_certificate_storage
    private_certificate_storage.location = str(tmp_path)
    now = timezone.now()
    organizer = User.objects.create_user(email='o@example.com', password='Strong12345!', full_name='Organizador', role='organizer', siape='10001')
    participant = User.objects.create_user(email='p@example.com', password='Strong12345!', full_name='Participante')
    event = Event.objects.create(title='Evento encerrado', description='Testes', event_type='Seminário', location='Campus', starts_at=now - timedelta(hours=4), ends_at=now - timedelta(hours=1), registration_opens_at=now - timedelta(days=5), registration_closes_at=now - timedelta(days=1), capacity=10, cover='events/example.png', organizer=organizer, created_by=organizer)
    EventSession.objects.create(event=event, starts_at=now - timedelta(hours=3), ends_at=now - timedelta(hours=2))
    reg = Registration.objects.create(user=participant, event=event)
    EventAttendance.objects.create(registration=reg, present=True, recorded_by=organizer)
    assert issue_pending()[0] == 1
    assert issue_pending()[0] == 0
    cert = Certificate.objects.get(event_attendance__registration=reg)
    assert cert.workload_minutes == 60 and cert.pdf.name.endswith('.pdf')
