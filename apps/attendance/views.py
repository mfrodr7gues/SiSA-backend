"""Registro e exportação de frequência por organizadores responsáveis.

Uma frequência ausente significa não marcada, e não ausência.
"""

from io import BytesIO
from xml.sax.saxutils import escape
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from apps.events.models import Event, Subevent
from apps.registrations.models import Registration, SubeventRegistration
from .models import EventAttendance, SubeventAttendance
from .serializers import EventAttendanceSerializer, SubeventAttendanceSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset.all()
        if self.request.user.role == 'organizer':
            return qs.filter(**{self.owner_path: self.request.user})
        # Administradores podem exercer a função de organizador em qualquer evento.
        if self.request.user.role == 'admin':
            return qs
        return qs.filter(**{self.participant_path: self.request.user})

    def check_record(self, registration):
        event = registration.event if hasattr(registration, 'event') else registration.registration.event
        activity = event if hasattr(registration, 'event') else registration.subevent
        is_responsible_organizer = (self.request.user.role == 'organizer' and event.organizer_id == self.request.user.pk)
        is_admin = self.request.user.role == 'admin'
        if not (is_responsible_organizer or is_admin):
            raise PermissionDenied('Somente o organizador responsável ou um administrador pode registrar frequência.')
        if activity.cancelled_at or event.cancelled_at or timezone.now() >= activity.ends_at:
            raise ValidationError('Frequência não pode ser alterada após o encerramento/cancelamento.')
        if registration.status != 'active':
            raise ValidationError('Inscrição não está ativa.')

    def perform_create(self, serializer):
        reg = serializer.validated_data[self.registration_field]
        self.check_record(reg)
        if self.queryset.filter(**{self.registration_field: reg}).exists():
            raise ValidationError('Frequência já registrada; atualize o registro existente.')
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        self.check_record(getattr(serializer.instance, self.registration_field))
        if self.registration_field in serializer.validated_data and serializer.validated_data[self.registration_field].pk != getattr(serializer.instance, self.registration_field + '_id'):
            raise ValidationError('Não é permitido transferir frequência.')
        serializer.save()

class EventAttendanceViewSet(AttendanceViewSet):
    queryset = EventAttendance.objects.select_related('registration__event', 'registration__user')
    serializer_class = EventAttendanceSerializer
    registration_field = 'registration'
    owner_path = 'registration__event__organizer'
    participant_path = 'registration__user'

class SubeventAttendanceViewSet(AttendanceViewSet):
    queryset = SubeventAttendance.objects.select_related('subevent_registration__subevent', 'subevent_registration__registration__event')
    serializer_class = SubeventAttendanceSerializer
    registration_field = 'subevent_registration'
    owner_path = 'subevent_registration__registration__event__organizer'
    participant_path = 'subevent_registration__registration__user'

class AttendanceSheetViewSet(viewsets.ViewSet):
    """Exporta uma lista de participantes e presenças para conferência/impressão."""
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        event = get_object_or_404(Event, pk=pk)
        is_responsible_organizer = (request.user.role == 'organizer' and event.organizer_id == request.user.pk)
        if not (is_responsible_organizer or request.user.role == 'admin'):
            raise PermissionDenied('Somente o organizador responsável ou um administrador pode baixar a lista.')
        registrations = Registration.objects.filter(event=event, status='active').select_related('user', 'attendance').order_by('user__full_name')
        rows = [['Participante', 'E-mail', 'Frequência']]
        for registration in registrations:
            attendance = getattr(registration, 'attendance', None)
            label = 'Não marcada' if attendance is None else 'Presente' if attendance.present else 'Ausente'
            rows.append([registration.user.full_name, registration.user.email, label])
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        title = Paragraph(f'Lista de frequência — {escape(event.title)}', styles['Heading1'])
        table_rows = [[Paragraph(escape(str(value)), styles['BodyText']) for value in row] for row in rows]
        table = Table(table_rows, colWidths=[150, 175, 100], repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
        document.build([title, Spacer(1, 14), table])
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'sisa-frequencia-{event.pk}.pdf', content_type='application/pdf')
