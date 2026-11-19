from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.events.models import Event, Subevent, EventSession, SubeventSession
from apps.registrations.models import Registration, SubeventRegistration, RegistrationHistory

@pytest.fixture
def setup_event(db):
    now = timezone.now()
    organizer = User.objects.create_user(email='organizer@example.com', password='Strong12345!', full_name='Organizador', role='organizer', siape='123456')
    participant = User.objects.create_user(email='participant@example.com', password='Strong12345!', full_name='Participante')
    event = Event.objects.create(title='Semana Acadêmica', description='Evento de testes', event_type='Seminário', location='Campus Cedro', starts_at=now + timedelta(days=5), ends_at=now + timedelta(days=6), registration_opens_at=now - timedelta(days=1), registration_closes_at=now + timedelta(days=4), capacity=2, cover='events/test.png', organizer=organizer, created_by=organizer)
    return (organizer, participant, event)

@pytest.mark.django_db
def test_enroll_cancel_reactivate_preserves_history(setup_event):
    organizer, user, event = setup_event
    client = APIClient()
    client.force_authenticate(user=user)
    r = client.post('/api/v1/registrations/enroll/', {'event': str(event.pk)}, format='json')
    assert r.status_code == 201, r.data
    reg = Registration.objects.get(user=user, event=event)
    assert client.post(f'/api/v1/registrations/{reg.pk}/cancel/').status_code == 200
    assert client.post(f'/api/v1/registrations/{reg.pk}/reactivate/').status_code == 200
    reg.refresh_from_db()
    assert reg.status == 'active'
    assert RegistrationHistory.objects.filter(registration=reg).count() == 3

@pytest.mark.django_db
def test_organizer_cannot_enroll_in_own_event(setup_event):
    organizer, user, event = setup_event
    client = APIClient()
    client.force_authenticate(user=organizer)
    assert client.post('/api/v1/registrations/enroll/', {'event': str(event.pk)}, format='json').status_code == 403

@pytest.mark.django_db
def test_conflicting_subevents_are_blocked(setup_event):
    organizer, user, event = setup_event
    now = timezone.now()
    sub1 = Subevent.objects.create(event=event, title='Oficina A', description='A', location='Sala 1', starts_at=event.starts_at + timedelta(hours=1), ends_at=event.starts_at + timedelta(hours=3), capacity=2)
    sub2 = Subevent.objects.create(event=event, title='Oficina B', description='B', location='Sala 2', starts_at=event.starts_at + timedelta(hours=2), ends_at=event.starts_at + timedelta(hours=4), capacity=2)
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.post('/api/v1/registrations/enroll/', {'event': str(event.pk)}, format='json').status_code == 201
    reg = Registration.objects.get(user=user, event=event)
    assert client.post(f'/api/v1/registrations/{reg.pk}/subevents/', {'subevent': str(sub1.pk)}, format='json').status_code == 201
    assert client.post(f'/api/v1/registrations/{reg.pk}/subevents/', {'subevent': str(sub2.pk)}, format='json').status_code == 400

@pytest.mark.django_db
def test_cancel_event_cascades(setup_event):
    organizer, user, event = setup_event
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.post('/api/v1/registrations/enroll/', {'event': str(event.pk)}, format='json').status_code == 201
    client.force_authenticate(user=organizer)
    assert client.post(f'/api/v1/events/{event.pk}/cancel/').status_code == 200
    assert Registration.objects.get(user=user, event=event).status == 'cancelled'
    assert RegistrationHistory.objects.filter(registration__event=event, reason='event_cancelled').exists()

@pytest.mark.django_db
def test_admin_can_enroll_even_when_responsible_for_event(setup_event):
    organizer, participant, event = setup_event
    admin = User.objects.create_superuser(email='admin-enroll@example.com', password='Strong12345!', full_name='Admin')
    # Administrador assume a responsabilidade pelo evento e também pode participar.
    event.organizer = admin
    event.save(update_fields=['organizer'])

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post('/api/v1/registrations/enroll/', {'event': str(event.pk)}, format='json')
    assert response.status_code == 201, response.data
    assert Registration.objects.filter(event=event, user=admin, status='active').exists()
