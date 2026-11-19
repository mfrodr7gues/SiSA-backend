from rest_framework import serializers
from .models import EventAttendance, SubeventAttendance

class EventAttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventAttendance
        fields = ['id', 'registration', 'present', 'recorded_by', 'recorded_at', 'updated_at']
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at']

class SubeventAttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubeventAttendance
        fields = ['id', 'subevent_registration', 'present', 'recorded_by', 'recorded_at', 'updated_at']
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at']
