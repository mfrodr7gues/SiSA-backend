"""Operações de eventos e atividades, com verificação de responsáveis.

Cancelamentos preservam o histórico e são executados em transações.
"""

from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.common import ensure
from apps.administration.audit import audit
from apps.registrations.models import Registration, SubeventRegistration, RegistrationHistory
from .models import Event, Subevent, EventSession, SubeventSession
from .serializers import EventSerializer, SubeventSerializer, EventSessionSerializer, SubeventSessionSerializer
from .services import may_manage

class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.select_related('organizer', 'created_by').all().order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('search'):
            qs = qs.filter(Q(title__icontains=p['search']) | Q(description__icontains=p['search']) | Q(event_type__icontains=p['search']))
        if p.get('type'):
            qs = qs.filter(event_type__iexact=p['type'])
        if p.get('status'):
            qs = [e.pk for e in qs if e.status == p['status']]
            return Event.objects.filter(pk__in=qs).order_by('-created_at')
        return qs

    def perform_create(self, serializer):
        ensure(self.request.user.is_authenticated and self.request.user.is_active and (self.request.user.role in ('organizer', 'admin')), 'Somente organizadores e administradores.')
        if self.request.user.role == 'organizer' and serializer.validated_data['organizer'] != self.request.user:
            raise PermissionDenied('Organizador só pode criar eventos próprios.')
        obj = serializer.save(created_by=self.request.user)
        audit(self.request.user, 'event_created', obj)

    def perform_update(self, serializer):
        obj = self.get_object()
        ensure(may_manage(self.request.user, obj), 'Sem permissão.')
        if 'organizer' in serializer.validated_data and serializer.validated_data['organizer'] != obj.organizer and (self.request.user.role != 'admin'):
            raise PermissionDenied('Somente administrador substitui responsável.')
        old = str(obj.organizer_id)
        obj = serializer.save()
        audit(self.request.user, 'event_updated', obj, before={'organizer': old}, after={'organizer': str(obj.organizer_id)})

    def perform_destroy(self, obj):
        ensure(may_manage(self.request.user, obj), 'Sem permissão.')
        if obj.registrations.exists() or obj.subevents.exists() or obj.sessions.exists():
            raise ValidationError('Evento com histórico/atividades não pode ser excluído; cancele-o.')
        audit(self.request.user, 'event_deleted', obj, after={'title': obj.title})
        obj.delete()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            obj = Event.objects.select_for_update().get(pk=self.get_object().pk)
            ensure(may_manage(request.user, obj), 'Sem permissão.')
            if obj.ends_at <= timezone.now():
                raise ValidationError('Evento finalizado não pode ser cancelado.')
            if obj.cancelled_at:
                raise ValidationError('Evento já cancelado.')
            now = timezone.now()
            obj.cancelled_at = now
            obj.save(update_fields=['cancelled_at'])
            for reg in obj.registrations.filter(status='active'):
                reg.status = 'cancelled'
                reg.cancelled_at = now
                reg.save(update_fields=['status', 'cancelled_at'])
                RegistrationHistory.objects.create(registration=reg, action='cancelled', previous_status='active', new_status='cancelled', actor=request.user, reason='event_cancelled')
                for child in reg.subevent_registrations.filter(status='active'):
                    child.status = 'cancelled'
                    child.cancelled_at = now
                    child.save(update_fields=['status', 'cancelled_at'])
                    RegistrationHistory.objects.create(registration=reg, subevent_registration=child, action='cancelled', previous_status='active', new_status='cancelled', actor=request.user, reason='event_cancelled')
            obj.subevents.filter(cancelled_at__isnull=True).update(cancelled_at=now)
            audit(request.user, 'event_cancelled', obj)
        return Response({'detail': 'Evento cancelado e inscrições encerradas.'})

class SubeventViewSet(viewsets.ModelViewSet):
    queryset = Subevent.objects.select_related('event').all()
    serializer_class = SubeventSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('event'):
            qs = qs.filter(event_id=self.request.query_params['event'])
        return qs

    def perform_create(self, serializer):
        ensure(may_manage(self.request.user, serializer.validated_data['event']), 'Sem permissão.')
        obj = serializer.save()
        audit(self.request.user, 'subevent_created', obj)

    def perform_update(self, serializer):
        obj = self.get_object()
        ensure(may_manage(self.request.user, obj.event), 'Sem permissão.')
        obj = serializer.save()
        audit(self.request.user, 'subevent_updated', obj)

    def perform_destroy(self, obj):
        ensure(may_manage(self.request.user, obj.event), 'Sem permissão.')
        if obj.registrations.exists() or obj.sessions.exists():
            raise ValidationError('Subevento com histórico/sessões não pode ser excluído.')
        audit(self.request.user, 'subevent_deleted', obj)
        obj.delete()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        obj = self.get_object()
        ensure(may_manage(request.user, obj.event), 'Sem permissão.')
        if obj.ends_at <= timezone.now() or obj.event.cancelled_at:
            raise ValidationError('Atividade encerrada ou evento cancelado.')
        with transaction.atomic():
            obj = Subevent.objects.select_for_update().get(pk=obj.pk)
            if obj.cancelled_at:
                raise ValidationError('Subevento já cancelado.')
            now = timezone.now()
            obj.cancelled_at = now
            obj.save(update_fields=['cancelled_at'])
            for reg in obj.registrations.filter(status='active'):
                reg.status = 'cancelled'
                reg.cancelled_at = now
                reg.save(update_fields=['status', 'cancelled_at'])
                RegistrationHistory.objects.create(registration=reg.registration, subevent_registration=reg, action='cancelled', previous_status='active', new_status='cancelled', actor=request.user, reason='subevent_cancelled')
            audit(request.user, 'subevent_cancelled', obj)
        return Response({'detail': 'Subevento cancelado.'})

class SessionViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        return self.queryset.all()

    def check_parent(self, parent):
        ensure(may_manage(self.request.user, parent if isinstance(parent, Event) else parent.event), 'Sem permissão.')

    def perform_create(self, serializer):
        parent = serializer.validated_data.get('event') or serializer.validated_data.get('subevent')
        self.check_parent(parent)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self.check_parent(getattr(obj, 'event', None) or obj.subevent)
        serializer.save()

    def perform_destroy(self, obj):
        parent = getattr(obj, 'event', None) or obj.subevent
        self.check_parent(parent)
        if parent.ends_at <= timezone.now():
            raise ValidationError('Atividade finalizada.')
        obj.delete()

class EventSessionViewSet(SessionViewSet):
    queryset = EventSession.objects.all()
    serializer_class = EventSessionSerializer

class SubeventSessionViewSet(SessionViewSet):
    queryset = SubeventSession.objects.all()
    serializer_class = SubeventSessionSerializer
