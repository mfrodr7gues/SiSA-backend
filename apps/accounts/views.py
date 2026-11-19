"""Endpoints de conta: autenticação JWT, perfil e recuperação de acesso.

As permissões são verificadas no servidor; o frontend não deve decidir sozinho
quem pode acessar cada operação.
"""

import secrets
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .models import User, RecoveryCode
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, ChangePasswordSerializer, ChangeEmailSerializer, RecoveryRequestSerializer, RecoveryResetSerializer, RecoveryVerifySerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: inline_serializer(name='LoginResponse', fields={'access': serializers.CharField(), 'refresh': serializers.CharField(), 'user': UserSerializer()})})
    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': UserSerializer(user, context={'request': request}).data})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data['refresh']).blacklist()
        except Exception:
            return Response({'detail': 'Refresh token inválido.'}, status=400)
        return Response(status=204)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class PasswordRecoveryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RecoveryRequestSerializer, responses={200: OpenApiResponse(description='Se a conta existir, enviaremos o código.')})
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            code = f'{secrets.randbelow(1000000):06d}'
            RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
            RecoveryCode.objects.create(user=user, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=15))
            send_mail('SiSA — recuperação de senha', f'Seu código de recuperação é {code}. Válido por 15 minutos.', settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return Response({'detail': 'Se a conta existir, enviaremos um código de recuperação.'})

class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RecoveryResetSerializer, responses={200: OpenApiResponse(description='Senha redefinida.')})
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        email = str(request.data.get('email', '')).strip().lower()
        code = str(request.data.get('code', ''))
        password = request.data.get('new_password', '')
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        record = RecoveryCode.objects.filter(user=user, used_at__isnull=True).order_by('-created_at').first() if user else None
        if not record or record.expires_at <= timezone.now() or record.attempts >= 5:
            return Response({'detail': 'Código inválido ou expirado.'}, status=400)
        record.attempts += 1
        record.save(update_fields=['attempts'])
        if not check_password(code, record.code_hash):
            return Response({'detail': 'Código inválido ou expirado.'}, status=400)
        try:
            validate_password(password, user)
        except ValidationError as e:
            return Response({'new_password': e.messages}, status=400)
        with transaction.atomic():
            user.set_password(password)
            user.save(update_fields=['password'])
            record.used_at = timezone.now()
            record.save(update_fields=['used_at'])
        return Response({'detail': 'Senha redefinida.'})

class PasswordRecoveryVerifyView(APIView):
    """Valida o código antes de exibir a etapa de nova senha no React."""
    permission_classes = [AllowAny]

    @extend_schema(request=RecoveryVerifySerializer, responses={200: OpenApiResponse(description='Código válido.')})
    def post(self, request):
        serializer = RecoveryVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        record = RecoveryCode.objects.filter(user=user, used_at__isnull=True).order_by('-created_at').first() if user else None
        if not record or record.expires_at <= timezone.now() or record.attempts >= 5:
            return Response({'detail': 'Código inválido ou expirado.'}, status=400)
        record.attempts += 1
        record.save(update_fields=['attempts'])
        if not check_password(code, record.code_hash):
            return Response({'detail': 'Código inválido ou expirado.'}, status=400)
        return Response({'detail': 'Código válido.'})

class ChangePasswordView(APIView):
    """Troca a senha de uma sessão autenticada, exigindo a senha atual."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: OpenApiResponse(description='Senha alterada.')})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Senha alterada. Faça login novamente.'})

class ChangeEmailView(APIView):
    """Atualiza o e-mail principal, mantendo username sincronizado."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangeEmailSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.email = serializer.validated_data['new_email'].lower()
        request.user.save(update_fields=['email', 'username'])
        return Response(UserSerializer(request.user, context={'request': request}).data)
