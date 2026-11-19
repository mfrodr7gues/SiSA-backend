"""Inscrições e cancelamentos com controle transacional de vagas.

O bloqueio do evento/subevento evita exceder a capacidade em acessos simultâneos.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.events.models import Event, Subevent
from apps.events.services import may_manage
from .models import Registration, SubeventRegistration, RegistrationHistory
from .serializers import RegistrationSerializer, SubeventRegistrationSerializer, RegistrationHistorySerializer

def check_registration_window(event):
    now = timezone.now()
    if event.cancelled_at or not event.registration_opens_at <= now < event.registration_closes_at or now >= event.starts_at:
        raise ValidationError('Inscrições indisponíveis neste momento.')

def record(reg, action, old, new, actor, reason='', child=None):
    RegistrationHistory.objects.create(registration=reg, subevent_registration=child, action=action, previous_status=old, new_status=new, actor=actor, reason=reason)

class RegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Registration.objects.select_related('event', 'user').prefetch_related('subevent_registrations__subevent')
        user = self.request.user
        # Administradores acumulam as permissões de participante e organizador.
        # O administrador pode consultar as inscrições do sistema para exercer a gestão global.
        if user.role == 'admin':
            return qs
        if user.role == 'organizer':
            return qs.filter(user=user) | qs.filter(event__organizer=user)
        return qs.filter(user=user)

    @action(detail=False, methods=['get'], url_path='me')
    def mine(self, request):
        qs = Registration.objects.filter(user=request.user).select_related('event').prefetch_related('subevent_registrations__subevent')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(RegistrationSerializer(page, many=True).data)
        return Response(RegistrationSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='enroll')
    def enroll(self, request):
        # O administrador também pode participar, inclusive de eventos sob sua responsabilidade.
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=request.data.get('event'))
            check_registration_window(event)
            if event.organizer_id == request.user.pk and request.user.role != 'admin':
                raise PermissionDenied('Organizador não pode participar do próprio evento.')
            reg = Registration.objects.filter(event=event, user=request.user).first()
            if reg and reg.status == 'active':
                raise ValidationError('Você já está inscrito.')
            if event.registrations.filter(status='active').count() >= event.capacity:
                raise ValidationError('Evento sem vagas.')
            if reg:
                reg.status = 'active'
                reg.reactivated_at = timezone.now()
                reg.cancelled_at = None
                reg.save(update_fields=['status', 'reactivated_at', 'cancelled_at'])
                record(reg, 'reactivated', 'cancelled', 'active', request.user)
            else:
                reg = Registration.objects.create(event=event, user=request.user)
                record(reg, 'created', '', 'active', request.user)
        return Response(RegistrationSerializer(reg, context={'request': request}).data, status=201)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            reg = Registration.objects.select_for_update().select_related('event').get(pk=self.get_object().pk)
            if reg.user_id != request.user.pk:
                raise PermissionDenied('Inscrição de outro usuário.')
            if reg.status != 'active' or reg.event.starts_at <= timezone.now():
                raise ValidationError('Cancelamento indisponível.')
            reg.status = 'cancelled'
            reg.cancelled_at = timezone.now()
            reg.save(update_fields=['status', 'cancelled_at'])
            record(reg, 'cancelled', 'active', 'cancelled', request.user, 'voluntary')
            for child in reg.subevent_registrations.filter(status='active'):
                child.status = 'cancelled'
                child.cancelled_at = timezone.now()
                child.save(update_fields=['status', 'cancelled_at'])
                record(reg, 'cancelled', 'active', 'cancelled', request.user, 'parent_cancelled', child)
        return Response({'detail': 'Inscrição cancelada.'})

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        reg = self.get_object()
        if reg.user_id != request.user.pk:
            raise PermissionDenied('Inscrição de outro usuário.')
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=reg.event_id)
            check_registration_window(event)
            if reg.status != 'cancelled':
                raise ValidationError('Inscrição não está cancelada.')
            if event.organizer_id == request.user.pk and request.user.role != 'admin':
                raise PermissionDenied('Organizador não pode participar do próprio evento.')
            if event.registrations.filter(status='active').count() >= event.capacity:
                raise ValidationError('Evento sem vagas.')
            reg.status = 'active'
            reg.cancelled_at = None
            reg.reactivated_at = timezone.now()
            reg.save(update_fields=['status', 'cancelled_at', 'reactivated_at'])
            record(reg, 'reactivated', 'cancelled', 'active', request.user)
        return Response(RegistrationSerializer(reg).data)

    @action(detail=True, methods=['post'])
    def subevents(self, request, pk=None):
        with transaction.atomic():
            reg = Registration.objects.select_for_update().select_related('event').get(pk=self.get_object().pk)
            if reg.user_id != request.user.pk:
                raise PermissionDenied('Inscrição de outro usuário.')
            check_registration_window(reg.event)
            if reg.status != 'active':
                raise ValidationError('Inscrição principal não está ativa.')
            sub = Subevent.objects.select_for_update().get(pk=request.data.get('subevent'))
            if sub.event_id != reg.event_id or sub.cancelled_at or sub.starts_at <= timezone.now():
                raise ValidationError('Subevento indisponível.')
            child = SubeventRegistration.objects.filter(registration=reg, subevent=sub).first()
            if child and child.status == 'active':
                raise ValidationError('Já inscrito neste subevento.')
            if sub.registrations.filter(status='active').count() >= sub.capacity:
                raise ValidationError('Subevento sem vagas.')
            others = SubeventRegistration.objects.filter(registration=reg, status='active').exclude(subevent=sub).select_related('subevent')
            for other in others:
                left = list(sub.sessions.values_list('starts_at', 'ends_at')) or [(sub.starts_at, sub.ends_at)]
                right = list(other.subevent.sessions.values_list('starts_at', 'ends_at')) or [(other.subevent.starts_at, other.subevent.ends_at)]
                if any((a < d and c < b for a, b in left for c, d in right)):
                    raise ValidationError('Conflito de horários com outro subevento inscrito.')
            if child:
                child.status = 'active'
                child.reactivated_at = timezone.now()
                child.cancelled_at = None
                child.save(update_fields=['status', 'reactivated_at', 'cancelled_at'])
                record(reg, 'reactivated', 'cancelled', 'active', request.user, child=child)
            else:
                child = SubeventRegistration.objects.create(registration=reg, subevent=sub)
                record(reg, 'created', '', 'active', request.user, child=child)
        return Response(SubeventRegistrationSerializer(child).data, status=201)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        reg = self.get_object()
        if reg.user_id != request.user.pk and request.user.role != 'admin' and (reg.event.organizer_id != request.user.pk):
            raise PermissionDenied('Sem permissão.')
        return Response(RegistrationHistorySerializer(reg.history.order_by('created_at'), many=True).data)

class SubeventRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubeventRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SubeventRegistration.objects.select_related('registration__event', 'registration__user', 'subevent')
        if self.request.user.role == 'admin':
            return qs
        if self.request.user.role == 'organizer':
            return qs.filter(registration__user=self.request.user) | qs.filter(registration__event__organizer=self.request.user)
        return qs.filter(registration__user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            child = SubeventRegistration.objects.select_for_update().select_related('registration', 'subevent').get(pk=self.get_object().pk)
            if child.registration.user_id != request.user.pk:
                raise PermissionDenied('Sem permissão.')
            if child.status != 'active' or child.subevent.starts_at <= timezone.now():
                raise ValidationError('Cancelamento indisponível.')
            child.status = 'cancelled'
            child.cancelled_at = timezone.now()
            child.save(update_fields=['status', 'cancelled_at'])
            record(child.registration, 'cancelled', 'active', 'cancelled', request.user, 'voluntary', child)
        return Response({'detail': 'Participação cancelada.'})
