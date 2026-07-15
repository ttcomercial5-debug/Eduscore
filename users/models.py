from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import random

from datetime import timedelta

from django.utils import timezone

from django.contrib.auth.hashers import (
    make_password,
    check_password,
)


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
        ("SUPERADMIN", "Super Admin"),
        ("DIRETOR", "Diretor"),
        ("DIRETOR_PEDAGOGICO", "Diretor Pedagógico"),
        ("PROFESSOR", "Professor"),
        ("ALUNO", "Aluno"),
        ("FINANCEIRO", "Financeiro"),
        ("SECRETARIA", "Secretaria"),
    )



    role = models.CharField(
        max_length=25,
        choices=ROLE_CHOICES,
        default="ALUNO",
        verbose_name="Perfil"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )

    escola = models.ForeignKey(
        "academic.Escola",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="Escola"
    )

    # =====================================================
    # CONTACTOS
    # =====================================================

    telefone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Telefone"
    )

    telefone_verificado = models.BooleanField(
        default=False,
        verbose_name="Telefone Verificado"
    )

    email_verificado = models.BooleanField(
        default=False,
        verbose_name="Email Verificado"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    # =====================================================
    # SEGURANÇA
    # =====================================================

    tentativas_login = models.PositiveIntegerField(
        default=0
    )

    bloqueado_ate = models.DateTimeField(
        null=True,
        blank=True
    )

    otp_codigo = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name="OTP"
    )

    otp_expira_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expira em"
    )

    otp_tentativas = models.PositiveIntegerField(
        default=0,
        verbose_name="Tentativas OTP"
    )

    ultimo_envio_otp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Último envio OTP"
    )

    objects = UserManager()

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        if self.is_superuser or self.role == "SUPERADMIN":
            return super().save(*args, **kwargs)

        if not self.escola:
            raise ValueError(
                "Usuário precisa estar vinculado a uma escola."
            )

        return super().save(*args, **kwargs)

    # =====================================================
    # OTP
    # =====================================================

    def gerar_otp(self):
        """
        Gera um código OTP válido por 10 minutos.
        O código é armazenado de forma segura (hash).
        """

        codigo = str(random.randint(100000, 999999))

        self.otp_codigo = make_password(codigo)
        self.otp_expira_em = timezone.now() + timedelta(minutes=10)
        self.otp_tentativas = 0
        self.ultimo_envio_otp = timezone.now()

        self.save(update_fields=[
            "otp_codigo",
            "otp_expira_em",
            "otp_tentativas",
            "ultimo_envio_otp",
        ])

        return codigo

    def validar_otp(self, codigo):
        """
        Valida o código OTP informado pelo utilizador.
        """

        if not self.otp_codigo:
            return False

        if not self.otp_expira_em:
            return False

        if timezone.now() > self.otp_expira_em:
            return False

        if self.otp_tentativas >= 5:
            return False

        if not check_password(codigo, self.otp_codigo):

            self.otp_tentativas += 1

            self.save(update_fields=[
                "otp_tentativas"
            ])

            return False

        self.otp_codigo = None
        self.otp_expira_em = None
        self.otp_tentativas = 0

        self.save(update_fields=[
            "otp_codigo",
            "otp_expira_em",
            "otp_tentativas",
        ])

        return True

    # =====================================================
    # LOGIN
    # =====================================================

    def esta_bloqueado(self):
        """
        Verifica se a conta está temporariamente bloqueada.
        """

        if not self.bloqueado_ate:
            return False

        return timezone.now() < self.bloqueado_ate

    def registrar_falha_login(self):
        """
        Incrementa tentativas de login e bloqueia a conta
        por 15 minutos após 5 falhas consecutivas.
        """

        self.tentativas_login += 1

        if self.tentativas_login >= 5:
            self.bloqueado_ate = timezone.now() + timedelta(minutes=15)

        self.save(update_fields=[
            "tentativas_login",
            "bloqueado_ate",
        ])

    def limpar_tentativas_login(self):
        """
        Limpa tentativas de login após autenticação bem-sucedida.
        """

        self.tentativas_login = 0
        self.bloqueado_ate = None

        self.save(update_fields=[
            "tentativas_login",
            "bloqueado_ate",
        ])

    # =====================================================
    # REPRESENTAÇÃO
    # =====================================================

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"