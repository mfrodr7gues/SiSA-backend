"""Validação de entrada e representação de usuários.

Serializers validam dados antes de qualquer gravação no PostgreSQL.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, OrganizerRequest

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'role', 'siape', 'institutional_email', 'photo', 'biography', 'field_of_work', 'institutional_info', 'is_active', 'created_at']
        read_only_fields = ['id', 'role', 'email', 'siape', 'institutional_email', 'is_active', 'created_at']

class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    request_organizer = serializers.BooleanField(default=False)
    siape = serializers.CharField(required=False, allow_blank=True)
    institutional_email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        if User.objects.filter(email__iexact=data['email']).exists():
            raise serializers.ValidationError('E-mail já cadastrado.')
        if data['request_organizer']:
            if not data.get('siape') or not data.get('institutional_email'):
                raise serializers.ValidationError('SIAPE e e-mail institucional são obrigatórios.')
            if User.objects.filter(siape=data['siape']).exists() or OrganizerRequest.objects.filter(siape=data['siape'], status__in=['pending', 'approved']).exists():
                raise serializers.ValidationError('SIAPE já utilizado.')
        return data

    def create(self, data):
        request = data.pop('request_organizer')
        siape = data.pop('siape', '')
        institutional_email = data.pop('institutional_email', '')
        user = User.objects.create_user(**data)
        if request:
            OrganizerRequest.objects.create(user=user, siape=siape, institutional_email=institutional_email)
        return user

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text='E-mail para participantes/administradores; SIAPE para organizadores')
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data['identifier'].strip()
        if '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            user = User.objects.filter(siape=identifier, role='organizer').first()
        if user and user.role == 'organizer' and ('@' in identifier):
            raise serializers.ValidationError('Organizadores devem entrar com SIAPE.')
        if user and user.role != 'organizer' and ('@' not in identifier):
            raise serializers.ValidationError('Utilize seu e-mail.')
        user = authenticate(username=user.email, password=data['password']) if user else None
        if not user or not user.is_active:
            raise serializers.ValidationError('Credenciais inválidas.')
        data['user'] = user
        return data

class OrganizerRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = OrganizerRequest
        fields = ['id', 'user', 'siape', 'institutional_email', 'status', 'reviewed_by', 'justification', 'requested_at', 'reviewed_at']
        read_only_fields = fields

class RecoveryRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class RecoveryVerifySerializer(RecoveryRequestSerializer):
    code = serializers.CharField(min_length=6, max_length=6)

class RecoveryResetSerializer(RecoveryVerifySerializer):
    new_password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({'current_password': 'Senha atual incorreta.'})
        validate_password(data['new_password'], user)
        return data

class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({'current_password': 'Senha atual incorreta.'})
        if User.objects.filter(email__iexact=data['new_email']).exclude(pk=user.pk).exists():
            raise serializers.ValidationError({'new_email': 'E-mail já cadastrado.'})
        return data
