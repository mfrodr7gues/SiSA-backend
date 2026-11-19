"""Regras de negócio de eventos, subeventos e sessões.

Mantemos as validações aqui para reutilizá-las em diferentes endpoints.
"""

from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from apps.registrations.models import Registration, SubeventRegistration
from apps.common import ensure

def may_manage(user, event):
    return bool(user.is_authenticated and user.is_active and (user.role == 'admin' or (user.role == 'organizer' and event.organizer_id == user.pk)))

def validate_event(data, instance=None):

    def v(k):
        return data.get(k, getattr(instance, k, None))
    if v('starts_at') >= v('ends_at'):
        raise ValidationError('Período do evento inválido.')
    if v('registration_opens_at') >= v('registration_closes_at') or v('registration_closes_at') > v('starts_at'):
        raise ValidationError('Período de inscrições deve terminar até o início do evento.')
    if v('capacity') < 1:
        raise ValidationError('Capacidade deve ser positiva.')
    organizer = v('organizer')
    # Um administrador também pode assumir a responsabilidade por um evento.
    if not organizer or organizer.role not in ('organizer', 'admin') or (not organizer.is_active):
        raise ValidationError('O responsável deve ser organizador ou administrador ativo.')
    if instance:
        if instance.cancelled_at:
            raise ValidationError('Evento cancelado não pode ser alterado.')
        if instance.ends_at <= timezone.now():
            raise ValidationError('Evento finalizado não pode ser alterado.')
        if instance.registrations.filter(status='active').count() > v('capacity'):
            raise ValidationError('Capacidade menor que inscrições ativas.')
        if instance.subevents.filter(capacity__gt=v('capacity')).exists():
            raise ValidationError('Capacidade inferior à de subevento existente.')
        if instance.subevents.exclude(starts_at__gte=v('starts_at'), ends_at__lte=v('ends_at')).exists():
            raise ValidationError('Subeventos fora do novo período.')
        if instance.sessions.exclude(starts_at__gte=v('starts_at'), ends_at__lte=v('ends_at')).exists():
            raise ValidationError('Sessões fora do novo período.')
        if (v('starts_at') != instance.starts_at or v('ends_at') != instance.ends_at) and instance.registrations.filter(status='active').exists():
            raise ValidationError('Não é permitido alterar período de evento com inscrições ativas.')

def validate_subevent(data, instance=None):

    def v(k):
        return data.get(k, getattr(instance, k, None))
    event = v('event')
    if not event or event.cancelled_at or event.ends_at <= timezone.now():
        raise ValidationError('Evento indisponível.')
    if v('starts_at') >= v('ends_at') or v('starts_at') < event.starts_at or v('ends_at') > event.ends_at:
        raise ValidationError('Período do subevento fora do evento.')
    if v('capacity') < 1 or v('capacity') > event.capacity:
        raise ValidationError('Capacidade inválida para o subevento.')
    if instance:
        if instance.cancelled_at or instance.ends_at <= timezone.now():
            raise ValidationError('Subevento encerrado/cancelado.')
        if instance.registrations.filter(status='active').count() > v('capacity'):
            raise ValidationError('Capacidade inferior às inscrições ativas.')
        if instance.sessions.exclude(starts_at__gte=v('starts_at'), ends_at__lte=v('ends_at')).exists():
            raise ValidationError('Sessões fora do período.')
        if v('event').pk != instance.event_id:
            raise ValidationError('Não é permitido transferir subevento de evento.')

def session_validation(data, instance=None):

    def v(k):
        return data.get(k, getattr(instance, k, None))
    parent = v('event') if 'event' in data or (instance and hasattr(instance, 'event_id')) else v('subevent')
    if not parent:
        raise ValidationError('Atividade obrigatória.')
    if instance and parent.pk != (instance.event_id if hasattr(instance, 'event_id') else instance.subevent_id):
        raise ValidationError('Não é permitido transferir sessão entre atividades.')
    if parent.cancelled_at or parent.ends_at <= timezone.now():
        raise ValidationError('Atividade encerrada ou cancelada.')
    if v('starts_at') >= v('ends_at') or v('starts_at') < parent.starts_at or v('ends_at') > parent.ends_at:
        raise ValidationError('Sessão fora do período da atividade.')
    sessions = parent.sessions.exclude(pk=instance.pk if instance else None)
    if sessions.filter(starts_at__lt=v('ends_at'), ends_at__gt=v('starts_at')).exists():
        raise ValidationError('Sessões da mesma atividade não podem se sobrepor.')
    if instance and (v('starts_at') != instance.starts_at or v('ends_at') != instance.ends_at):
        if not hasattr(parent, 'event_type') and parent.registrations.filter(status='active').exists():
            active = SubeventRegistration.objects.filter(subevent=parent, status='active').select_related('registration')
            for reg in active:
                other = SubeventRegistration.objects.filter(registration=reg.registration, status='active').exclude(subevent=parent).select_related('subevent')
                for other_reg in other:
                    if other_reg.subevent.sessions.filter(starts_at__lt=v('ends_at'), ends_at__gt=v('starts_at')).exists():
                        raise ValidationError('Alteração criaria conflito com inscrição existente.')
