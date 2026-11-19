from rest_framework import serializers
from .models import Event, Subevent, EventSession, SubeventSession
from .services import validate_event, validate_subevent, session_validation

class EventSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    organizer_name = serializers.CharField(source='organizer.full_name', read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'event_type', 'location', 'starts_at', 'ends_at', 'registration_opens_at', 'registration_closes_at', 'capacity', 'cover', 'organizer', 'organizer_name', 'created_by', 'cancelled_at', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'cancelled_at', 'created_at', 'updated_at']

    def validate(self, data):
        validate_event(data, self.instance)
        return data

class SubeventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subevent
        fields = ['id', 'event', 'title', 'description', 'location', 'starts_at', 'ends_at', 'capacity', 'cover', 'cancelled_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'cancelled_at', 'created_at', 'updated_at']

    def validate(self, data):
        validate_subevent(data, self.instance)
        return data

class EventSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventSession
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        session_validation(data, self.instance)
        return data

class SubeventSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubeventSession
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        session_validation(data, self.instance)
        return data
