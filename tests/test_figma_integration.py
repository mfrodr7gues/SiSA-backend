"""Testes de regressão dos endpoints adicionados após revisão das telas."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
def test_change_password_requires_current_password():
    user = User.objects.create_user(
        email="student@example.com",
        password="OldPassword!123",
        full_name="Participante Teste",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/users/me/change-password/",
        {"current_password": "incorrect", "new_password": "NewPassword!123"},
        format="json",
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/change-password/",
        {"current_password": "OldPassword!123", "new_password": "NewPassword!123"},
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NewPassword!123")


@pytest.mark.django_db
def test_change_email_updates_login_identifier():
    user = User.objects.create_user(
        email="before@example.com",
        password="ExamplePassword!123",
        full_name="Participante Teste",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/users/me/change-email/",
        {"current_password": "ExamplePassword!123", "new_email": "after@example.com"},
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "after@example.com"
    assert user.username == "after@example.com"


@pytest.mark.django_db
def test_recovery_verification_rejects_unknown_code():
    client = APIClient()
    response = client.post(
        "/api/v1/auth/password-recovery/verify/",
        {"email": "unknown@example.com", "code": "123456"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_participant_cannot_download_attendance_sheet():
    user = User.objects.create_user(
        email="student@example.com",
        password="ExamplePassword!123",
        full_name="Participante Teste",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/attendance-sheets/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == 404

@pytest.mark.django_db
def test_admin_can_record_attendance_for_event():
    from datetime import timedelta
    from django.utils import timezone
    from rest_framework.test import APIClient
    from apps.accounts.models import User
    from apps.events.models import Event
    from apps.registrations.models import Registration
    from apps.attendance.models import EventAttendance

    now = timezone.now()
    admin = User.objects.create_superuser(email='admin-attendance@example.com', password='Strong12345!', full_name='Admin')
    participant = User.objects.create_user(email='participant-attendance@example.com', password='Strong12345!', full_name='Participante')
    event = Event.objects.create(
        title='Evento para frequência', description='Teste', event_type='Oficina', location='Campus Cedro',
        starts_at=now + timedelta(hours=1), ends_at=now + timedelta(days=1),
        registration_opens_at=now - timedelta(days=1), registration_closes_at=now + timedelta(minutes=30),
        capacity=10, cover='events/test.png', organizer=admin, created_by=admin,
    )
    registration = Registration.objects.create(event=event, user=participant)
    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post('/api/v1/event-attendance/', {'registration': str(registration.pk), 'present': True}, format='json')
    assert response.status_code in (200, 201), response.data
    assert EventAttendance.objects.filter(registration=registration, present=True, recorded_by=admin).exists()
