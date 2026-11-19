from rest_framework import serializers
from .models import Certificate

class CertificateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Certificate
        fields = ['id', 'code', 'participant_name', 'activity_name', 'workload_minutes', 'activity_starts_at', 'activity_ends_at', 'institution', 'issued_at']
