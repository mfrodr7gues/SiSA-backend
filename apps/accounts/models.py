from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from apps.common import UUIDModel

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('E-mail obrigatório')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, username=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(role='admin', is_staff=True, is_superuser=True, is_active=True)
        return self.create_user(email, password, **extra)

class User(AbstractUser, UUIDModel):
    ROLE_CHOICES = [('participant', 'Participante'), ('organizer', 'Organizador'), ('admin', 'Administrador')]
    username = models.CharField(max_length=254, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')
    siape = models.CharField(max_length=30, unique=True, null=True, blank=True)
    institutional_email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to='profiles/', blank=True)
    biography = models.TextField(blank=True)
    field_of_work = models.CharField(max_length=150, blank=True)
    institutional_info = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.email

class OrganizerRequest(UUIDModel):
    STATUS = [('pending', 'Pendente'), ('approved', 'Aprovada'), ('rejected', 'Rejeitada')]
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='organizer_requests')
    siape = models.CharField(max_length=30)
    institutional_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_organizer_requests')
    justification = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

class RecoveryCode(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_codes')
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
