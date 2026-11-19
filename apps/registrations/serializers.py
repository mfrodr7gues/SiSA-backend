from rest_framework import serializers
from .models import Registration, SubeventRegistration, RegistrationHistory

class SubeventRegistrationSerializer(serializers.ModelSerializer):
    subevent_title = serializers.CharField(source='subevent.title', read_only=True)

    class Meta:
        model = SubeventRegistration
        fields = ['id', 'registration', 'subevent', 'subevent_title', 'status', 'registered_at', 'cancelled_at', 'reactivated_at']
        read_only_fields = fields

class RegistrationSerializer(serializers.ModelSerializer):
    subevent_registrations = SubeventRegistrationSerializer(many=True, read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Registration
        fields = ['id', 'user', 'event', 'event_title', 'status', 'registered_at', 'cancelled_at', 'reactivated_at', 'subevent_registrations']
        read_only_fields = fields

class RegistrationHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = RegistrationHistory
        fields = '__all__'
