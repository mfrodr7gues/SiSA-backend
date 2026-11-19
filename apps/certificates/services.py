"""Emissão de certificados PDF com QR Code para validação pública.

A carga horária é calculada pelas sessões cadastradas da atividade.
"""

from io import BytesIO
from datetime import timedelta
import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, A4
from xml.sax.saxutils import escape
from .models import Certificate
from apps.attendance.models import EventAttendance, SubeventAttendance

def workload(activity):
    return sum((int((s.ends_at - s.starts_at).total_seconds() // 60) for s in activity.sessions.all()))

def create_pdf(cert):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=52, rightMargin=52, topMargin=60, bottomMargin=45)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CertTitleSisa', parent=styles['Title'], fontSize=27, leading=33, alignment=TA_CENTER, spaceAfter=32, textColor=colors.HexColor('#124f5d')))
    styles.add(ParagraphStyle(name='CertBodySisa', parent=styles['Normal'], fontSize=15, leading=25, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='CertFooterSisa', parent=styles['Normal'], fontSize=9, leading=14, alignment=TA_CENTER))
    name = escape(cert.participant_name)
    title = escape(cert.activity_name)
    hours = f'{cert.workload_minutes // 60}h{cert.workload_minutes % 60:02d}min'
    start = timezone.localtime(cert.activity_starts_at).strftime('%d/%m/%Y %H:%M')
    end = timezone.localtime(cert.activity_ends_at).strftime('%d/%m/%Y %H:%M')
    verify = f'{settings.PUBLIC_BASE_URL}/api/v1/certificates/verify/{cert.code}/'
    qr = qrcode.make(verify)
    qrbuf = BytesIO()
    qr.save(qrbuf, format='PNG')
    qrbuf.seek(0)
    story = [Paragraph('CERTIFICADO DE PARTICIPAÇÃO', styles['CertTitleSisa']), Paragraph(f'Certificamos que <b>{name}</b> participou da atividade <b>{title}</b>, realizada no período de {start} a {end}, com carga horária de <b>{hours}</b>.', styles['CertBodySisa']), Spacer(1, 26), Paragraph(escape(cert.institution), styles['CertBodySisa']), Spacer(1, 15), Image(qrbuf, width=86, height=86), Spacer(1, 9), Paragraph(f'Código de autenticidade: {escape(cert.code)}', styles['CertFooterSisa']), Paragraph(escape(verify), styles['CertFooterSisa'])]
    doc.build(story)
    return buffer.getvalue()

def issue_pending():
    now = timezone.now()
    issued = 0
    skipped = 0
    for attendance in EventAttendance.objects.filter(present=True, registration__status='active', registration__event__ends_at__lte=now, registration__event__cancelled_at__isnull=True).select_related('registration__user', 'registration__event'):
        activity = attendance.registration.event
        if hasattr(attendance, 'certificate'):
            continue
        minutes = workload(activity)
        if not minutes:
            skipped += 1
            continue
        cert = Certificate.objects.create(event_attendance=attendance, participant_name=attendance.registration.user.full_name, activity_name=activity.title, workload_minutes=minutes, activity_starts_at=activity.starts_at, activity_ends_at=activity.ends_at)
        cert.pdf.save(f'{cert.id}.pdf', ContentFile(create_pdf(cert)), save=True)
        issued += 1
    for attendance in SubeventAttendance.objects.filter(present=True, subevent_registration__status='active', subevent_registration__registration__status='active', subevent_registration__subevent__ends_at__lte=now, subevent_registration__subevent__cancelled_at__isnull=True, subevent_registration__registration__event__cancelled_at__isnull=True).select_related('subevent_registration__registration__user', 'subevent_registration__subevent'):
        activity = attendance.subevent_registration.subevent
        if hasattr(attendance, 'certificate'):
            continue
        minutes = workload(activity)
        if not minutes:
            skipped += 1
            continue
        cert = Certificate.objects.create(subevent_attendance=attendance, participant_name=attendance.subevent_registration.registration.user.full_name, activity_name=activity.title, workload_minutes=minutes, activity_starts_at=activity.starts_at, activity_ends_at=activity.ends_at)
        cert.pdf.save(f'{cert.id}.pdf', ContentFile(create_pdf(cert)), save=True)
        issued += 1
    return (issued, skipped)
