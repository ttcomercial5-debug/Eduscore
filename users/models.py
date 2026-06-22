from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Manager personalizado para garantir criação correta de usuários
    """

    def create_user(self, username, email=None, password=None, **extra_fields):

        if not username:
            raise ValueError("O usuário deve ter um username.")

        email = self.normalize_email(email)

        extra_fields.setdefault("role", "ALUNO")

        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """
        Sempre cria SUPERADMIN
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "SUPERADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa ter is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa ter is_superuser=True.")

        user = self.create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields
        )

        return user


class User(AbstractUser):

    ROLE_CHOICES = (
        ('SUPERADMIN', 'Super Admin'),
        ('DIRETOR', 'Diretor'),
        ('DIRETOR_PEDAGOGICO', 'Diretor Pedagogico'),
        ('PROFESSOR', 'Professor'),
        ('ALUNO', 'Aluno'),
        ('FINANCEIRO', 'Financeiro'),
        ('SECRETARIA', 'Secretaria'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='ALUNO'
    )

    ativo = models.BooleanField(default=True)

    escola = models.ForeignKey(
        'academic.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="usuarios"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    # Segurança Login

    tentativas_login = models.PositiveIntegerField(
        default=0
    )

    bloqueado_ate = models.DateTimeField(
        null=True,
        blank=True
    )

    # Manager personalizado
    objects = UserManager()

    def save(self, *args, **kwargs):
        """
        Regras SaaS:

        SUPERADMIN → pode não ter escola
        superuser Django → pode não ter escola
        outros usuários → devem ter escola
        """

        if self.is_superuser or self.role == 'SUPERADMIN':
            super().save(*args, **kwargs)
            return

        if not self.escola:
            raise ValueError("Usuário precisa estar vinculado a uma escola.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"