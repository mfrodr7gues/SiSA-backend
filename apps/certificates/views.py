from django.http import FileResponse, Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q
from .models import Certificate
from .serializers import CertificateSerializer

class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(Q(event_attendance__registration__user=self.request.user) | Q(subevent_attendance__subevent_registration__registration__user=self.request.user)).distinct()

    @action(detail=False, methods=['get'], url_path='me')
    def mine(self, request):
        return self.list(request)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        cert = self.get_object()
        if not cert.pdf:
            raise Http404('PDF indisponível')
        return FileResponse(cert.pdf.open('rb'), as_attachment=True, filename=f'SiSA-certificado-{cert.id}.pdf', content_type='application/pdf')

class CertificateVerifyViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def retrieve(self, request, pk=None):
        cert = Certificate.objects.filter(code=pk).first()
        if not cert:
            return Response({'valid': False, 'detail': 'Certificado não encontrado.'}, status=404)
        return Response({'valid': True, **CertificateSerializer(cert).data})
