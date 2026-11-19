import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, OrganizerRequest

@pytest.mark.django_db
def test_registration_and_login():
    client = APIClient()
    r = client.post('/api/v1/auth/register/', {'full_name': 'Estudante Exemplo', 'email': 'estudante@example.com', 'password': 'Senha-Forte-2026!'}, format='json')
    assert r.status_code == 201, r.data
    user = User.objects.get(email='estudante@example.com')
    assert user.role == 'participant' and user.check_password('Senha-Forte-2026!')
    r = client.post('/api/v1/auth/login/', {'identifier': 'estudante@example.com', 'password': 'Senha-Forte-2026!'}, format='json')
    assert r.status_code == 200 and 'access' in r.data

@pytest.mark.django_db
def test_organizer_request_needs_admin_approval():
    client = APIClient()
    r = client.post('/api/v1/auth/register/', {'full_name': 'Organizador Solicitante', 'email': 'organizer@example.com', 'password': 'Senha-Forte-2026!', 'request_organizer': True, 'siape': '123456', 'institutional_email': 'organizer@ifce.edu.br'}, format='json')
    assert r.status_code == 201, r.data
    user = User.objects.get(email='organizer@example.com')
    assert user.role == 'participant'
    assert OrganizerRequest.objects.get(user=user).status == 'pending'

@pytest.mark.django_db
def test_admin_can_promote_organizer_to_admin_and_demote_after_reassignment():
    from datetime import timedelta
    from django.utils import timezone
    from apps.events.models import Event

    admin = User.objects.create_superuser(email='admin@example.com', password='Strong12345!', full_name='Administradora')
    organizer = User.objects.create_user(email='organizer-role@example.com', password='Strong12345!', full_name='Organizador', role='organizer', siape='SIAPE-100', institutional_email='org@ifce.edu.br')
    client = APIClient()
    client.force_authenticate(user=admin)

    # A promoção preserva a responsabilidade por eventos existentes.
    response = client.post(f'/api/v1/admin/users/{organizer.pk}/change-role/', {'role': 'admin'}, format='json')
    assert response.status_code == 200, response.data
    organizer.refresh_from_db()
    assert organizer.role == 'admin'

    # Cria um evento futuro sob responsabilidade do usuário promovido.
    now = timezone.now()
    event = Event.objects.create(
        title='Evento sob responsabilidade', description='Teste', event_type='Seminário',
        location='Campus Cedro', starts_at=now + timedelta(days=3), ends_at=now + timedelta(days=4),
        registration_opens_at=now - timedelta(days=1), registration_closes_at=now + timedelta(days=2),
        capacity=10, cover='events/test.png', organizer=organizer, created_by=admin,
    )

    response = client.post(f'/api/v1/admin/users/{organizer.pk}/change-role/', {'role': 'participant'}, format='json')
    assert response.status_code == 400
    assert 'events_to_reassign' in response.data

    # Depois de transferir a responsabilidade, o rebaixamento é permitido.
    replacement = User.objects.create_user(email='replacement@example.com', password='Strong12345!', full_name='Novo Organizador', role='organizer', siape='SIAPE-200')
    event.organizer = replacement
    event.save(update_fields=['organizer'])
    response = client.post(f'/api/v1/admin/users/{organizer.pk}/change-role/', {'role': 'participant'}, format='json')
    assert response.status_code == 200, response.data
    organizer.refresh_from_db()
    assert organizer.role == 'participant'
    assert organizer.siape is None
