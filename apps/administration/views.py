"""Operações restritas a administradores, incluindo aprovação e auditoria.
"""

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.common import IsAdmin
from apps.accounts.models import User, OrganizerRequest
from apps.accounts.serializers import UserSerializer, OrganizerRequestSerializer
from apps.events.models import Event
from apps.events.services import validate_event
from apps.registrations.models import Registration
from apps.certificates.models import Certificate
from .models import AuditLog
from .serializers import AuditLogSerializer
from .audit import audit

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by('-date_joined')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(full_name__icontains=search) | qs.filter(email__icontains=search)
        return qs

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        old = user.is_active
        user.is_active = True
        user.save(update_fields=['is_active'])
        audit(request.user, 'user_activated', user, before={'active': old}, after={'active': True})
        return Response({'detail': 'Usuário ativado.'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ValidationError('Não é permitido inativar a própria conta.')
        if user.role in ('organizer', 'admin') and user.organized_events.filter(cancelled_at__isnull=True, ends_at__gt=timezone.now()).exists():
            raise ValidationError('Transfira os eventos sob responsabilidade deste usuário antes de inativá-lo.')
        user.is_active = False
        user.save(update_fields=['is_active'])
        audit(request.user, 'user_deactivated', user, after={'active': False})
        return Response({'detail': 'Usuário inativado.'})

    @action(detail=True, methods=['post'], url_path='change-role')
    def change_role(self, request, pk=None):
        """Altera o perfil de um organizador, preservando eventos e histórico."""
        target_role = request.data.get('role')
        if target_role not in ('admin', 'participant'):
            raise ValidationError({'role': 'Informe admin ou participant.'})

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=self.get_object().pk)
            if user.role != 'organizer':
                raise ValidationError('Somente usuários organizadores podem ter o perfil alterado por esta operação.')
            if user.pk == request.user.pk:
                raise ValidationError('Não é permitido alterar o próprio perfil.')

            # Eventos futuros ou em andamento precisam ter outro responsável antes do rebaixamento.
            active_events = user.organized_events.filter(
                cancelled_at__isnull=True,
                ends_at__gt=timezone.now(),
            )
            if target_role == 'participant' and active_events.exists():
                raise ValidationError({
                    'detail': 'Transfira a responsabilidade de todos os eventos ativos/futuros antes de rebaixar o organizador.',
                    'events_to_reassign': list(active_events.values_list('id', flat=True)),
                })

            old_role = user.role
            user.role = target_role
            # SIAPE e e-mail institucional deixam de identificar um organizador após o rebaixamento.
            if target_role == 'participant':
                user.siape = None
                user.institutional_email = ''
                user.save(update_fields=['role', 'siape', 'institutional_email'])
            else:
                user.save(update_fields=['role'])

            audit(
                request.user,
                'user_role_changed',
                user,
                before={'role': old_role},
                after={'role': target_role},
            )

        return Response({'detail': 'Perfil atualizado.', 'user': UserSerializer(user).data})

    @action(detail=True, methods=['post'], url_path='revoke-organizer')
    def revoke_organizer(self, request, pk=None):
        user = self.get_object()
        if user.role != 'organizer':
            raise ValidationError('Usuário não é organizador.')
        if user.organized_events.filter(cancelled_at__isnull=True, ends_at__gt=timezone.now()).exists():
            raise ValidationError('Reatribua os eventos antes de revogar a permissão.')
        user.role = 'participant'
        user.siape = None
        user.institutional_email = ''
        user.save(update_fields=['role', 'siape', 'institutional_email'])
        audit(request.user, 'user_role_changed', user, before={'role': 'organizer'}, after={'role': 'participant'})
        return Response({'detail': 'Permissão revogada.'})

class OrganizerRequestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = OrganizerRequestSerializer
    queryset = OrganizerRequest.objects.select_related('user', 'reviewed_by').all().order_by('-requested_at')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        with transaction.atomic():
            req = OrganizerRequest.objects.select_for_update().select_related('user').get(pk=self.get_object().pk)
            if req.status != 'pending':
                raise ValidationError('Solicitação já analisada.')
            if not req.user.is_active:
                raise ValidationError('Usuário inativo não pode ser aprovado.')
            if User.objects.filter(siape=req.siape).exclude(pk=req.user_id).exists():
                raise ValidationError('SIAPE já utilizado.')
            user = req.user
            user.role = 'organizer'
            user.siape = req.siape
            user.institutional_email = req.institutional_email
            user.save(update_fields=['role', 'siape', 'institutional_email'])
            req.status = 'approved'
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            audit(request.user, 'organizer_approved', user)
        return Response({'detail': 'Organizador aprovado.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        req = self.get_object()
        if req.status != 'pending':
            raise ValidationError('Solicitação já analisada.')
        req.status = 'rejected'
        req.justification = request.data.get('justification', '')
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save(update_fields=['status', 'justification', 'reviewed_by', 'reviewed_at'])
        audit(request.user, 'organizer_rejected', req)
        return Response({'detail': 'Solicitação rejeitada.'})

class OrganizerReassignmentView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=pk)
            organizer = User.objects.filter(pk=request.data.get('organizer'), role='organizer', is_active=True).first()
            if not organizer:
                raise ValidationError('Organizador aprovado e ativo obrigatório.')
            validate_event({'organizer': organizer}, event)
            old = str(event.organizer_id)
            event.organizer = organizer
            event.save(update_fields=['organizer'])
            audit(request.user, 'organizer_reassigned', event, before={'organizer': old}, after={'organizer': str(organizer.pk)})
        return Response({'detail': 'Responsável atualizado.'})

class DashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({'users': User.objects.count(), 'events': Event.objects.count(), 'registrations': Registration.objects.count(), 'issued_certificates': Certificate.objects.count()})

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()
