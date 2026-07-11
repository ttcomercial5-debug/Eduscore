from django.contrib.auth.middleware import get_user
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, IntegerField
from django.db.models.functions import Cast
from datetime import datetime
from datetime import date
import uuid


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================


from django.db import models
from django.core.cache import cache
from datetime import date


# =====================================================
# UTILIDADE GLOBAL (ANO LETIVO)
# =====================================================
def get_ano_letivo_atual():
    """
    Ano letivo baseado no calendário escolar:
    Início em Setembro
    Ex: 2026/2027
    """
    hoje = date.today()

    if hoje.month >= 9:
        inicio = hoje.year
        fim = hoje.year + 1
    else:
        inicio = hoje.year - 1
        fim = hoje.year

    return f"{inicio}/{fim}"


class Configuracao(models.Model):

    # =========================
    # SISTEMA
    # =========================
    nome_sistema = models.CharField(max_length=200, default="Gestão Escolar Pro")
    logo_sistema = models.ImageField(upload_to='logos_sistema/', blank=True, null=True)
    favicon = models.ImageField(upload_to='favicon/', blank=True, null=True)

    cor_principal = models.CharField(max_length=7, default="#2563eb")
    cor_secundaria = models.CharField(max_length=7, default="#1e40af")

    # =========================
    # ANO LETIVO
    # =========================
    ano_letivo_padrao = models.CharField(
        max_length=20,
        default=get_ano_letivo_atual,
        blank=True,
        null=True
    )

    # =========================
    # ESCOLAS
    # =========================
    ativar_novas_escolas = models.BooleanField(default=True)
    limite_alunos_por_escola = models.PositiveIntegerField(default=1000)
    limite_turmas_por_escola = models.PositiveIntegerField(default=20)

    PLANO_CHOICES = [
        ("basico", "Básico"),
        ("medio", "Médio"),
        ("premium", "Premium"),
    ]

    plano_padrao = models.CharField(
        max_length=20,
        choices=PLANO_CHOICES,
        default="basico"
    )

    armazenamento_por_escola_mb = models.PositiveIntegerField(default=1024)

    # =========================
    # FINANCEIRO GLOBAL
    # =========================
    moeda = models.CharField(max_length=10, default="Kz")

    valor_mensal_plano_basico = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=25000
    )

    valor_anual_plano_basico = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=250000
    )

    cobranca_automatica = models.BooleanField(default=False)

    # =========================
    # SEGURANÇA
    # =========================
    login_ativo = models.BooleanField(default=True)
    tempo_sessao_minutos = models.PositiveIntegerField(default=120)
    bloqueio_tentativas_login = models.PositiveIntegerField(default=5)
    backup_automatico = models.BooleanField(default=True)

    # =========================
    # MANUTENÇÃO GLOBAL
    # =========================
    modo_manutencao = models.BooleanField(default=False)
    mensagem_manutencao = models.TextField(blank=True, null=True)

    # =========================
    # SINGLETON (CACHE GLOBAL)
    # =========================
    @classmethod
    def get_solo(cls):
        """
        Retorna configuração global com cache.
        Garante apenas 1 instância ativa.
        """
        cache_key = "configuracao_global"

        obj = cache.get(cache_key)
        if obj:
            return obj

        obj = cls.objects.first()

        if not obj:
            obj = cls.objects.create()

        cache.set(cache_key, obj, 60 * 10)  # 10 minutos

        return obj

    def save(self, *args, **kwargs):

        cache.delete("configuracao_global")
        super().save(*args, **kwargs)

    def __str__(self):
        return "Configuração Global"


# ==========================================================
# PAGAMENTO DO PLANO SAAS (Escola paga você)
# ==========================================================

from django.db import models
from django.utils import timezone


class PagamentoPlano(models.Model):

    STATUS_PENDENTE = 'PENDENTE'
    STATUS_PAGO = 'PAGO'
    STATUS_ATRASADO = 'ATRASADO'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_PAGO, 'Pago'),
        (STATUS_ATRASADO, 'Atrasado'),
    ]

    escola = models.ForeignKey(
        'academic.Escola',
        on_delete=models.CASCADE,
        related_name='pagamentos_planos'
    )

    plano = models.ForeignKey(
        'academic.Plano',
        on_delete=models.PROTECT,
        related_name='pagamentos'
    )

    mes_referencia = models.CharField(max_length=20)  # Ex: Janeiro 2026

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data_vencimento = models.DateField()

    data_pagamento = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE
    )

    observacao = models.TextField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    def atualizar_status(self):

        hoje = timezone.now().date()

        if self.data_pagamento:
            self.status = self.STATUS_PAGO

        elif hoje > self.data_vencimento:
            self.status = self.STATUS_ATRASADO

        else:
            self.status = self.STATUS_PENDENTE

        self.save(update_fields=["status"])



class Plano(models.Model):
    nome = models.CharField(
        max_length=100,
        unique=True
    )

    limite_alunos = models.PositiveIntegerField()

    valor_mensal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    ativo = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.nome


# ==========================================================
# ESCOLA
# ==========================================================

from django.db import models
from django.utils import timezone
from datetime import date
import uuid

class Escola(models.Model):

    nome = models.CharField(
        "Nome da Escola",
        max_length=255
    )

    # =====================================
    # CÓDIGO MULTI-SAAS
    # =====================================

    codigo = models.CharField(
        "Código da Escola",
        max_length=10,
        unique=True,
        blank=True,
        help_text="Código usado no login da escola"
    )

    logo = models.ImageField(
        upload_to='logos_escolas/',
        blank=True,
        null=True
    )

    endereco = models.CharField(
        "Endereço",
        max_length=255
    )

    provincia = models.CharField(
        "Província",
        max_length=100,
        blank=True,
        null=True
    )

    municipio = models.CharField(
        "Município",
        max_length=100,
        blank=True,
        null=True
    )

    telefone = models.CharField(
        "Telefone",
        max_length=20
    )

    nif = models.CharField(
        "NIF",
        max_length=14,
        blank=True,
        null=True,
        help_text="Número de Identificação Fiscal da escola"
    )

    email = models.EmailField(
        "Email da Escola",
        max_length=254,
        blank=True,
        null=True,
        help_text="Email oficial da escola"
    )

    plano = models.ForeignKey(
        "Plano",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escolas",
        verbose_name="Plano"
    )

    data_expiracao = models.DateField(
        "Data de Expiração do Plano",
        null=True,
        blank=True
    )

    ativo = models.BooleanField(
        "Ativo",
        default=True
    )

    criada_em = models.DateTimeField(
        "Criada em",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Escola"
        verbose_name_plural = "Escolas"
        ordering = ["nome"]

    # ======================================================
    # SAVE
    # ======================================================

    def save(self, *args, **kwargs):

        escola_nova = self.pk is None

        # =====================================
        # GERAR CÓDIGO AUTOMÁTICO
        # =====================================

        if not self.codigo:
            self.codigo = str(uuid.uuid4().int)[:6]

        super().save(*args, **kwargs)

        # =====================================
        # CRIAR ANO LETIVO AUTOMÁTICO
        # =====================================

        if escola_nova:

            # IMPORTAÇÃO LOCAL
            from .models import AnoLetivo

            ano_inicio = date.today().year
            ano_fim = ano_inicio + 1

            nome_ano = f"{ano_inicio}/{ano_fim}"

            # =====================================
            # VERIFICAR SE JÁ EXISTE
            # =====================================

            ano_existente = AnoLetivo.objects.filter(
                escola=self,
                nome=nome_ano
            ).first()

            if not ano_existente:

                # DESATIVAR OUTROS ANOS
                AnoLetivo.objects.filter(
                    escola=self
                ).update(ativo=False)

                # CRIAR NOVO ANO ATIVO
                AnoLetivo.objects.create(
                    escola=self,
                    nome=nome_ano,
                    ativo=True
                )

    # ======================================================
    # VERIFICAR SE ESCOLA ESTÁ ATIVA
    # ======================================================

    def esta_ativa(self):

        if not self.ativo:
            return False

        if (
            self.data_expiracao
            and self.data_expiracao < timezone.now().date()
        ):
            return False

        return True

    def __str__(self):
        return f"{self.nome} ({self.codigo})"



# ==========================================================
# ANO LETIVO
# ==========================================================

class AnoLetivo(models.Model):
    nome = models.CharField(max_length=20)  # Ex: 2025/2026
    ativo = models.BooleanField(default=True)

    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="anos_letivos"
    )

    def __str__(self):
        return self.nome




# ==========================================================
# TURMA
# ==========================================================

class Turma(models.Model):

    CLASSE_CHOICES = [
        ('0', 'Iniciação'),
        ('1', '1ª Classe'),
        ('2', '2ª Classe'),
        ('3', '3ª Classe'),
        ('4', '4ª Classe'),
        ('5', '5ª Classe'),
        ('6', '6ª Classe'),
        ('7', '7ª Classe'),
        ('8', '8ª Classe'),
        ('9', '9ª Classe'),
        ('10', '10ª Classe'),
        ('11', '11ª Classe'),
        ('12', '12ª Classe'),
        ('13', '13ª Classe'),
    ]

    TURNOS = [
        ('MANHA', 'Manhã'),
        ('TARDE', 'Tarde'),
        ('NOITE', 'Noite'),
    ]

    classe = models.CharField(
        max_length=10,
        choices=CLASSE_CHOICES,
        verbose_name="Classe"
    )

    curso = models.ForeignKey(
        'Curso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turmas",
        verbose_name="Curso"
    )

    identificador = models.CharField(
        max_length=5,
        verbose_name="Identificador"
    )

    turno = models.CharField(
        max_length=10,
        choices=TURNOS,
        default='MANHA',
        verbose_name='Turno'
    )

    ano_letivo = models.ForeignKey(
        'AnoLetivo',
        on_delete=models.CASCADE,
        related_name="turmas",
        verbose_name="Ano Letivo"
    )

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name="turmas",
        verbose_name="Escola"
    )

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="turmas",
        limit_choices_to={"role": "PROFESSOR"},
        null=True,
        blank=True,
        verbose_name="Professor"
    )

    criada_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['classe', 'identificador', 'turno', 'ano_letivo', 'escola', 'curso'],
                name='unique_turma_por_curso'
            )
        ]
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def nome_completo(self):
        return f"{self.get_classe_display()} {self.identificador} - {self.get_turno_display()} - {self.ano_letivo}"

    def __str__(self):
        return self.nome_completo()

    @staticmethod
    def ordenar_queryset(queryset):
        """
        Ordenação numérica correta da classe.
        """
        return queryset.annotate(
            classe_int=Cast('classe', IntegerField())
        ).order_by('classe_int', 'identificador')




# ==========================================================
# DISCIPLINA
# ==========================================================

class Disciplina(models.Model):

    nome = models.CharField(max_length=90)

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="disciplinas"
    )

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESSOR'},
        related_name="disciplinas",
        null=True,
        blank=True
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="disciplinas"
    )

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('nome', 'turma', 'escola')
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.turma}"


# ==========================================================
# MODEL: ALUNO
# ==========================================================

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg


class Aluno(models.Model):

    SEXO_CHOICES = [
        ("Masculino", "Masculino"),
        ("Feminino", "Feminino"),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "ALUNO"},
        related_name="perfil_aluno"
    )

    # ==========================================================
    # CURSO
    # ==========================================================

    curso = models.ForeignKey(
        "Curso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos",
        verbose_name="Curso"
    )

    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    matricula = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Matrícula"
    )

    numero_processo = models.CharField(
        max_length=20,
        verbose_name="Número de Processo"
    )

    numero_bi = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número do BI"
    )

    # ==========================================================
    # DADOS PESSOAIS
    # ==========================================================

    data_nascimento = models.DateField(
        null=True,
        blank=True
    )

    sexo = models.CharField(
        max_length=15,
        choices=SEXO_CHOICES,
        null=True,
        blank=True
    )

    # ==========================================================
    # DADOS ESCOLARES
    # ==========================================================

    classe = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )

    turma = models.ForeignKey(
        "academic.Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos"
    )

    numero_na_turma = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        related_name="alunos"
    )

    escola = models.ForeignKey(
        "academic.Escola",
        on_delete=models.CASCADE,
        related_name="alunos"
    )

    # ==========================================================
    # CONTROLO DE MATRÍCULA
    # ==========================================================

    matricula_confirmada = models.BooleanField(
        default=False
    )

    ultimo_ano_confirmado = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos_confirmados",
        verbose_name="Último Ano Confirmado"
    )

    precisa_confirmacao = models.BooleanField(
        default=False
    )

    # ==========================================================
    # RESULTADOS
    # ==========================================================

    media_final = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    aprovado = models.BooleanField(
        default=False
    )

    # ==========================================================
    # CONTROLO
    # ==========================================================

    ativo = models.BooleanField(
        default=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    # ==========================================================
    # META
    # ==========================================================

    class Meta:

        ordering = [
            "classe",
            "numero_na_turma",
            "usuario__first_name"
        ]

        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

        constraints = [

            models.UniqueConstraint(
                fields=["numero_processo", "escola"],
                name="unique_numero_processo_por_escola"
            ),

            models.UniqueConstraint(
                fields=["matricula", "escola"],
                name="unique_matricula_por_escola"
            )

        ]

        indexes = [

            models.Index(fields=["numero_processo"]),
            models.Index(fields=["numero_bi"]),
            models.Index(fields=["matricula"]),
            models.Index(fields=["escola"]),
            models.Index(fields=["ano_letivo"]),

        ]

    # ==========================================================
    # MÉDIA FINAL
    # ==========================================================

    def calcular_media_final(self, ano_letivo=None):

        ano = ano_letivo or self.ano_letivo

        notas = self.notas.filter(
            disciplina__turma__ano_letivo=ano
        )

        media = notas.aggregate(
            media=Avg("valor")
        )["media"]

        if media is not None:

            self.media_final = round(media, 2)

            self.aprovado = self.media_final >= 10

            self.save(
                update_fields=[
                    "media_final",
                    "aprovado"
                ]
            )

        return self.media_final or 0

    # ==========================================================
    # STATUS ESCOLAR
    # ==========================================================

    @property
    def status_escolar(self):

        if self.aprovado:
            return "APROVADO"

        return "REPROVADO"

    # ==========================================================
    # IDADE
    # ==========================================================

    @property
    def idade(self):

        if not self.data_nascimento:
            return None

        hoje = date.today()

        return (
            hoje.year
            - self.data_nascimento.year
            - (
                (hoje.month, hoje.day)
                <
                (
                    self.data_nascimento.month,
                    self.data_nascimento.day
                )
            )
        )

    # ==========================================================
    # NOME COMPLETO
    # ==========================================================

    @property
    def nome_completo(self):

        return (
            self.usuario.get_full_name()
            or
            self.usuario.username
        )

    # ==========================================================
    # PODE CONFIRMAR MATRÍCULA?
    # ==========================================================

    @property
    def pode_confirmar_matricula(self):

        if not self.precisa_confirmacao:
            return False

        if not self.ano_letivo:
            return False

        if (
            self.ultimo_ano_confirmado
            and
            self.ultimo_ano_confirmado == self.ano_letivo
        ):
            return False

        return True

    # ==========================================================
    # CONFIRMAR MATRÍCULA
    # ==========================================================

    def confirmar_matricula(self):

        self.matricula_confirmada = True

        self.precisa_confirmacao = False

        self.ultimo_ano_confirmado = self.ano_letivo

        self.save(
            update_fields=[
                "matricula_confirmada",
                "precisa_confirmacao",
                "ultimo_ano_confirmado"
            ]
        )

    # ==========================================================
    # LIMPAR / VALIDAR
    # ==========================================================

    def clean(self):

        if not self.numero_processo:
            raise ValidationError(
                "Número de processo é obrigatório."
            )

        if not self.matricula:
            raise ValidationError(
                "Matrícula é obrigatória."
            )

        if self.data_nascimento:

            hoje = date.today()

            if self.data_nascimento > hoje:

                raise ValidationError({
                    "data_nascimento":
                        "A data de nascimento não pode ser futura."
                })

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(self, *args, **kwargs):

        if self.turma:

            self.classe = self.turma.classe

            if hasattr(self.turma, "curso"):
                self.curso = self.turma.curso

        super().save(*args, **kwargs)

    # ==========================================================
    # REPRESENTAÇÃO
    # ==========================================================

    def __str__(self):

        return (
            f"{self.nome_completo} "
            f"- Proc: {self.numero_processo}"
        )




# ==========================================================
# NOTA
# ==========================================================

from decimal import Decimal
from django.db import models, transaction


class Nota(models.Model):

    TRIMESTRE_CHOICES = [
        (1, "1º Trimestre"),
        (2, "2º Trimestre"),
        (3, "3º Trimestre"),
    ]

    aluno = models.ForeignKey("Aluno", on_delete=models.CASCADE, related_name="notas")
    disciplina = models.ForeignKey("Disciplina", on_delete=models.CASCADE, related_name="notas")
    ano_letivo = models.ForeignKey("AnoLetivo", on_delete=models.CASCADE, related_name="notas")
    trimestre = models.IntegerField(choices=TRIMESTRE_CHOICES)

    # PROVAS
    p1 = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    p2 = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    exame = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    recurso = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    # MÉDIAS
    media = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    media_final = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    situacao = models.CharField(
        max_length=20,
        choices=[
            ("APROVADO", "Aprovado"),
            ("REPROVADO", "Reprovado"),
            ("RECURSO", "Recurso"),
        ],
        default="REPROVADO"
    )

    escola = models.ForeignKey("Escola", on_delete=models.CASCADE, related_name="notas")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("aluno", "disciplina", "trimestre", "ano_letivo")
        ordering = ["disciplina", "trimestre"]

    # =====================================================
    # ESCALA DE NOTAS (10 ou 20)
    # =====================================================
    def escala_maxima(self):
        try:
            classe = int(self.disciplina.turma.classe)
        except:
            return 20

        return 10 if classe <= 6 else 20

    # =====================================================
    # CONTROLO DE FECHO
    # =====================================================
    def etapa_fechada(self, etapa):
        from academic.models import FechamentoNota

        return FechamentoNota.objects.filter(
            disciplina=self.disciplina,
            trimestre=self.trimestre,
            ano_letivo=self.ano_letivo,
            etapa=etapa,
            fechado=True
        ).exists()

    # =====================================================
    # SAVE COM REGRAS
    # =====================================================
    def save(self, *args, **kwargs):
        from django.db import transaction
        from academic.models import FechamentoNota

        max_nota = self.escala_maxima()

        # =========================
        # NORMALIZAR VALORES
        # =========================
        def normalizar(valor):
            if valor is None:
                return None
            v = float(valor)
            return min(v, max_nota)

        p1 = normalizar(self.p1)
        p2 = normalizar(self.p2)
        exame = normalizar(self.exame)
        recurso = normalizar(self.recurso)

        # =========================
        # BLOQUEIO DE ETAPAS FECHADAS
        # =========================
        if self.pk:
            old = Nota.objects.get(pk=self.pk)

            for etapa, old_val, new_val in [
                ("P1", old.p1, self.p1),
                ("P2", old.p2, self.p2),
                ("EXAME", old.exame, self.exame),
                ("RECURSO", old.recurso, self.recurso),
            ]:
                if old_val != new_val:
                    if FechamentoNota.objects.filter(
                        disciplina=self.disciplina,
                        trimestre=self.trimestre,
                        ano_letivo=self.ano_letivo,
                        etapa=etapa,
                        fechado=True
                    ).exists():
                        raise ValueError(f"{etapa} está fechado")

        # =========================
        # MÉDIA BASE
        # =========================
        if p1 is not None and p2 is not None:
            media = Decimal(round((p1 + p2) / 2, 2))
        elif p1 is not None:
            media = Decimal(p1)
        else:
            media = None

        self.media = media

        # =========================
        # MÉDIA FINAL
        # =========================
        if media is not None:
            media_base = float(media)

            if exame is not None:
                media_base = round((media_base + float(exame)) / 2, 2)

            # RECURSO
            if media_base < (max_nota / 2) and recurso is not None:
                if float(recurso) > media_base:
                    media_base = float(recurso)

            self.media_final = Decimal(str(media_base))

            # SITUAÇÃO (ajustada à escala)
            self.situacao = (
                "APROVADO"
                if media_base >= (max_nota / 2)
                else "REPROVADO"
            )

        else:
            self.media_final = None
            self.situacao = "REPROVADO"

        super().save(*args, **kwargs)

        transaction.on_commit(lambda: self.atualizar_media_aluno())

    # =====================================================
    # MÉDIA GERAL DO ALUNO
    # =====================================================
    def atualizar_media_aluno(self):
        notas = Nota.objects.filter(
            aluno=self.aluno,
            ano_letivo=self.ano_letivo
        )

        medias = [
            float(n.media_final)
            for n in notas
            if n.media_final is not None
        ]

        if not medias:
            return

        media_geral = round(sum(medias) / len(medias), 2)
        negativas = len([m for m in medias if m < 10])

        self.aluno.media_final = media_geral
        self.aluno.aprovado = negativas <= 3

        self.aluno.save(update_fields=["media_final", "aprovado"])

    # =====================================================
    # STRING
    # =====================================================
    def __str__(self):
        return f"{self.aluno} | {self.disciplina.nome} | {self.ano_letivo} | T{self.trimestre}"



# ==========================================================
# FREQUÊNCIA
# ==========================================================

class Frequencia(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    data = models.DateField()

    presente = models.BooleanField(default=True)
    justificada = models.BooleanField(default=False)

    observacao = models.TextField(blank=True)

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("aluno", "disciplina", "data")
        ordering = ["-data", "disciplina"]


# ==========================================================
# TAREFA
# ==========================================================

class Tarefa(models.Model):

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    descricao = models.TextField()
    data_entrega = models.DateField()

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tarefa - {self.turma}"


# ==========================================================
# PROFESSOR
# ==========================================================

class Professor(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_professor"
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="professores"
    )

    disciplina = models.CharField(
        max_length=30
    )

    classes = models.CharField(
        max_length=30,
        help_text="Ex: 10ª, 11ª, 12ª"
    )

    turmas = models.ManyToManyField(
        Turma,
        related_name="professores",
        blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.disciplina}"


# ==========================================
# HORÁRIO
# ==========================================

class Horario(models.Model):

    DIAS_SEMANA = [
        (1, "Segunda-feira"),
        (2, "Terça-feira"),
        (3, "Quarta-feira"),
        (4, "Quinta-feira"),
        (5, "Sexta-feira"),
    ]

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="horarios"
    )

    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE
    )

    dia = models.CharField(max_length=3, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        ordering = ["dia", "hora_inicio"]

    def __str__(self):
        return f"{self.turma} - {self.disciplina} ({self.get_dia_display()})"


# ==========================================================
#                    MENSALIDADE
# ==========================================================

from decimal import Decimal
from django.db import models
from django.utils import timezone


class Mensalidade(models.Model):

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("PAGA", "Paga"),
        ("ATRASADA", "Atrasada"),
    ]

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="mensalidades"
    )

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        related_name="mensalidades"
    )

    mes = models.CharField(
        max_length=20
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vencimento = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDENTE"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("aluno", "mes", "ano_letivo")
        ordering = ["vencimento"]

    # ======================================================
    # TOTAL PAGO
    # ======================================================

    @property
    def total_pago(self):

        total = self.pagamentos.aggregate(
            total=models.Sum("valor_pago")
        )["total"]

        return total or Decimal("0.00")

    # ======================================================
    # VALOR RESTANTE
    # ======================================================

    @property
    def restante(self):

        restante = self.valor - self.total_pago

        if restante < 0:
            return Decimal("0.00")

        return restante

    # ======================================================
    # PAGO COMPLETAMENTE
    # ======================================================

    @property
    def esta_paga(self):

        return self.total_pago >= self.valor

    # ======================================================
    # STATUS AUTOMÁTICO
    # ======================================================

    def atualizar_status(self):
        hoje = timezone.now().date()

        if self.total_pago >= self.valor:
            novo_status = "PAGA"
        elif hoje > self.vencimento:
            novo_status = "ATRASADA"
        else:
            novo_status = "PENDENTE"

        if self.status != novo_status:
            self.status = novo_status
            self.save(update_fields=["status"])

    # ======================================================
    # SAVE
    # ======================================================

    def save(self, *args, **kwargs):

        # deixa mês padronizado
        if self.mes:
            self.mes = self.mes.strip().title()

        super().save(*args, **kwargs)

    # ======================================================
    # STRING
    # ======================================================

    def __str__(self):

        return (
            f"{self.aluno} | "
            f"{self.mes} | "
            f"{self.status}"
        )


# ==========================================================
#                    PAGAMENTO
# ==========================================================

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Pagamento(models.Model):

    FORMAS_PAGAMENTO = [
        ("DINHEIRO", "Dinheiro"),
        ("TRANSFERENCIA", "Transferência"),
        ("TPA", "TPA"),
        ("MULTICAIXA", "Multicaixa"),
        ("OUTRO", "Outro"),
    ]

    TIPOS = [
        ("MENSALIDADE", "Mensalidade"),
        ("INSCRICAO", "Inscrição"),
        ("UNIFORME", "Uniforme"),
        ("EXAME", "Exame"),
        ("DECLARACAO", "Declaração"),
        ("MULTA", "Multa"),
        ("OUTRO", "Outro"),
    ]

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="pagamentos",
        verbose_name="Aluno"
    )

    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="pagamentos",
        verbose_name="Escola"
    )

    mensalidade = models.ForeignKey(
        "Mensalidade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos",
        verbose_name="Mensalidade"
    )

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        related_name="pagamentos",
        verbose_name="Ano Letivo"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default="MENSALIDADE"
    )

    valor_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    forma_pagamento = models.CharField(
        max_length=20,
        choices=FORMAS_PAGAMENTO
    )

    numero_recibo = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    observacao = models.TextField(
        blank=True,
        null=True
    )

    recebido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_recebidos"
    )

    data_pagamento = models.DateTimeField(
        auto_now_add=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-criado_em"]

    # ======================================================
    # GERAR RECIBO
    # ======================================================

    def gerar_numero_recibo(self):

        if not self.ano_letivo:

            ano = "0000"

        else:

            try:
                ano = self.ano_letivo.nome.split("/")[-1]

            except:
                ano = self.ano_letivo.nome

        ultimo = Pagamento.objects.filter(
            numero_recibo__startswith=f"REC-{ano}"
        ).order_by("-id").first()

        if not ultimo or not ultimo.numero_recibo:

            return f"REC-{ano}-00001"

        try:

            ultimo_numero = int(
                ultimo.numero_recibo.split("-")[-1]
            )

        except:

            ultimo_numero = 0

        novo = ultimo_numero + 1

        return f"REC-{ano}-{str(novo).zfill(5)}"

    # ======================================================
    # SAVE
    # ======================================================

    def save(self, *args, **kwargs):

        # escola automática
        if not self.escola and self.aluno:

            self.escola = self.aluno.escola

        # ano letivo automático
        if not self.ano_letivo and self.escola:

            from .models import AnoLetivo

            ano = AnoLetivo.objects.filter(
                escola=self.escola,
                ativo=True
            ).first()

            if ano:
                self.ano_letivo = ano

        # recibo automático
        if not self.numero_recibo:

            self.numero_recibo = (
                self.gerar_numero_recibo()
            )

        super().save(*args, **kwargs)

        # atualiza status da mensalidade
        if self.mensalidade:

            self.mensalidade.atualizar_status()

    # ======================================================
    # STRING
    # ======================================================

    def __str__(self):

        return (
            f"{self.numero_recibo} | "
            f"{self.aluno} | "
            f"{self.valor_pago} Kz"
        )



# ============================================================
#                     MODELO BOLETIM
# ============================================================

from django.db import models
import uuid


class Boletim(models.Model):

    aluno = models.ForeignKey("Aluno", on_delete=models.CASCADE)
    codigo_validacao = models.CharField(max_length=20, unique=True)
    media_anual = models.DecimalField(max_digits=5, decimal_places=2)
    status_final = models.CharField(max_length=20)
    data_emissao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Boletim {self.aluno} - {self.codigo_validacao}"




# ==========================================================
# HISTÓRICO DE MATRÍCULA
# ==========================================================

class HistoricoMatricula(models.Model):

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="historico_matriculas"
    )

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        db_index=True
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    classe = models.CharField(max_length=10)

    curso = models.ForeignKey(
        "Curso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    numero_na_turma = models.PositiveIntegerField(null=True, blank=True)

    matricula = models.CharField(max_length=30)

    # 👇 snapshot correto da turma naquele ano
    total_alunos_turma = models.PositiveIntegerField(default=0)

    media_final = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    aprovado = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ano_letivo", "classe", "numero_na_turma"]
        unique_together = ("aluno", "ano_letivo")  #

    def __str__(self):
        return f"{self.aluno} - {self.ano_letivo} - {self.classe}"



# ============================================================
#                     HISTORICO ACADEMICO
# ============================================================

class HistoricoAcademico(models.Model):

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="historicos"
    )

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE
    )

    classe = models.CharField(
        max_length=10
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    curso = models.ForeignKey(
        "Curso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    media_final = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    situacao = models.CharField(
        max_length=20,
        choices=[
            ("APROVADO", "Aprovado"),
            ("REPROVADO", "Reprovado"),
            ("FINALISTA", "Finalista"),
            ("TRANSFERIDO", "Transferido"),
            ("DESISTENTE", "Desistente"),
        ]
    )

    matricula_confirmada = models.BooleanField(
        default=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-ano_letivo__nome"]

    def __str__(self):
        return (
            f"{self.aluno.nome_completo} - "
            f"{self.ano_letivo} - "
            f"{self.classe}"
        )


class HorarioTurma(models.Model):
    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="horarios_escola"
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.CASCADE,
        related_name="horarios_turma"
    )

    turno = models.CharField(
        max_length=10,
        choices=[
            ("MANHA", "Manhã"),
            ("TARDE", "Tarde"),
            ("NOITE", "Noite"),
        ]
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.turma} - {self.turno}"


class AulaHorario(models.Model):

    DIAS_SEMANA = [
        ("SEG", "Segunda"),
        ("TER", "Terça"),
        ("QUA", "Quarta"),
        ("QUI", "Quinta"),
        ("SEX", "Sexta"),
        ("SAB", "Sábado"),
    ]

    TIPO_CHOICES = [
        ("AULA", "Aula"),
        ("INTERVALO", "Intervalo"),
    ]

    horario = models.ForeignKey(
        HorarioTurma,
        on_delete=models.CASCADE,
        related_name="aulas"
    )

    dia = models.CharField(
        max_length=10,
        choices=DIAS_SEMANA
    )

    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default="AULA"
    )

    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    professor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        if self.tipo == "INTERVALO":
            return f"{self.get_dia_display()} - Intervalo"
        return f"{self.get_dia_display()} - {self.disciplina}"


class ConfiguracaoFinanceira(models.Model):

    escola = models.OneToOneField(
        Escola,
        on_delete=models.CASCADE
    )

    # ======================================================
    # MENSALIDADES POR CLASSE
    # ======================================================

    valor_mensalidade_iniciacao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_1 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_3 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_4 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_5 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_6 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_7 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_8 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_9 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_10 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_11 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_12 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_mensalidade_13 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ======================================================
    # OUTROS VALORES
    # ======================================================

    valor_multa_mensalidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_matricula = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_multa_matricula = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_declaracao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_exame = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ======================================================
    # OBTÉM A MENSALIDADE DA CLASSE
    # ======================================================

    def obter_valor_mensalidade(self, classe):

        mapa = {
            0: self.valor_mensalidade_iniciacao,
            1: self.valor_mensalidade_1,
            2: self.valor_mensalidade_2,
            3: self.valor_mensalidade_3,
            4: self.valor_mensalidade_4,
            5: self.valor_mensalidade_5,
            6: self.valor_mensalidade_6,
            7: self.valor_mensalidade_7,
            8: self.valor_mensalidade_8,
            9: self.valor_mensalidade_9,
            10: self.valor_mensalidade_10,
            11: self.valor_mensalidade_11,
            12: self.valor_mensalidade_12,
            13: self.valor_mensalidade_13,
        }

        return mapa.get(classe, 0)

    def __str__(self):
        return f"Financeiro - {self.escola.nome}"


class Curso(models.Model):

    nome = models.CharField(
        max_length=90,
        unique=True,
        verbose_name="Curso"
    )

    descricao = models.TextField(
        blank=True,
        null=True
    )

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name='cursos'
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

    def __str__(self):
        return self.nome


class Despesa(models.Model):

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name="despesas"
    )

    descricao = models.CharField(
        max_length=200,
        verbose_name="Descrição"
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor"
    )

    data = models.DateField(
        auto_now_add=True
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.descricao} - {self.valor} Kz"

from django.db import models

class Trimestre(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)           # "1º Trimestre", "2º Trimestre"
    ordem = models.PositiveSmallIntegerField()      # 1, 2, 3
    ano_letivo = models.CharField(max_length=20)    # "2025-2026"
    fechado = models.BooleanField(default=False)   # True = trimestre fechado

    class Meta:
        unique_together = ('escola', 'ano_letivo', 'ordem')
        ordering = ['ordem']

    def __str__(self):
        return f"{self.nome} ({self.ano_letivo}) - {'Fechado' if self.fechado else 'Aberto'}"

class FechamentoTrimestre(models.Model):

    disciplina = models.ForeignKey("Disciplina", on_delete=models.CASCADE)
    trimestre = models.IntegerField()
    ano_letivo = models.ForeignKey("AnoLetivo", on_delete=models.CASCADE)

    fechado = models.BooleanField(default=False)
    fechado_por = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)

    data_fechamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["disciplina", "trimestre", "ano_letivo"]


# ==========================================================
# FECHAMENTO DE ETAPAS DAS NOTAS
# ==========================================================

class FechamentoNota(models.Model):

    ETAPAS = [
        ("P1", "P1"),
        ("P2", "P2"),
        ("EXAME", "EXAME"),
        ("RECURSO", "RECURSO"),
    ]

    disciplina = models.ForeignKey(
        "Disciplina",
        on_delete=models.CASCADE
    )

    trimestre = models.IntegerField()

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE
    )

    etapa = models.CharField(
        max_length=10,
        choices=ETAPAS
    )

    fechado = models.BooleanField(
        default=False
    )

    fechado_por = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    data_fechamento = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        unique_together = (
            "disciplina",
            "trimestre",
            "ano_letivo",
            "etapa"
        )

    def __str__(self):
        return (
            f"{self.disciplina} | "
            f"T{self.trimestre} | "
            f"{self.etapa}"
        )



from django.db import models
from django.conf import settings

class Entrada(models.Model):

    escola = models.ForeignKey("Escola", on_delete=models.CASCADE)

    descricao = models.CharField(max_length=255)

    valor = models.DecimalField(max_digits=12, decimal_places=2)

    data = models.DateField(auto_now_add=True)

    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.descricao} - {self.valor} Kz"

def gerar_ano_automatico():

    ano_atual = datetime.now().year
    proximo_ano = ano_atual + 1

    return f"{ano_atual}/{proximo_ano}"



# ==========================================================
# CALENDÁRIO ESCOLAR INTELIGENTE
# ==========================================================

class CalendarioEscolar(models.Model):

    # ======================================================
    # TIPOS DE EVENTOS
    # ======================================================

    TIPOS = [

        ("PROVA", "Prova"),

        ("EVENTO", "Evento Escolar"),

        ("FERIAS", "Férias"),

        ("REUNIAO", "Reunião"),

        ("PAGAMENTO", "Pagamento"),

        ("ENCERRAMENTO", "Encerramento de Trimestre"),

        ("NOTA", "Lançamento de Notas"),

        ("AVISO", "Aviso Geral"),

    ]

    # ======================================================
    # PRIORIDADE
    # ======================================================

    PRIORIDADE_CHOICES = [

        ("BAIXA", "Baixa"),

        ("MEDIA", "Média"),

        ("ALTA", "Alta"),

        ("URGENTE", "Urgente"),

    ]

    # ======================================================
    # TÍTULO
    # ======================================================

    titulo = models.CharField(
        max_length=255
    )

    # ======================================================
    # DESCRIÇÃO
    # ======================================================

    descricao = models.TextField(
        blank=True,
        null=True
    )

    # ======================================================
    # TIPO
    # ======================================================

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    # ======================================================
    # PRIORIDADE
    # ======================================================

    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default="MEDIA"
    )

    # ======================================================
    # DATAS
    # ======================================================

    data_inicio = models.DateField()

    data_fim = models.DateField(
        null=True,
        blank=True
    )

    # ======================================================
    # HORÁRIO OPCIONAL
    # ======================================================

    hora_inicio = models.TimeField(
        null=True,
        blank=True
    )

    hora_fim = models.TimeField(
        null=True,
        blank=True
    )

    # ======================================================
    # ESCOLA
    # ======================================================

    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="eventos_calendario"
    )

    # ======================================================
    # ANO LETIVO
    # ======================================================

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        related_name="eventos_calendario"
    )

    # ======================================================
    # TURMA
    # ======================================================

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos"
    )

    # ======================================================
    # EVENTO GERAL
    # ======================================================

    evento_geral = models.BooleanField(
        default=True
    )

    # ======================================================
    # VISIBILIDADE
    # ======================================================

    mostrar_para_diretor = models.BooleanField(
        default=True
    )

    mostrar_para_professor = models.BooleanField(
        default=False
    )

    mostrar_para_aluno = models.BooleanField(
        default=False
    )

    mostrar_para_secretaria = models.BooleanField(
        default=False
    )

    # ======================================================
    # NOTIFICAÇÃO
    # ======================================================

    enviar_notificacao = models.BooleanField(
        default=True
    )

    # ======================================================
    # STATUS
    # ======================================================

    ativo = models.BooleanField(
        default=True
    )

    # ======================================================
    # CRIADOR
    # ======================================================

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="eventos_criados"
    )

    # ======================================================
    # DATA CRIAÇÃO
    # ======================================================

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    # ======================================================
    # META
    # ======================================================

    class Meta:

        ordering = [

            "-prioridade",
            "data_inicio",
            "-criado_em"

        ]

        verbose_name = "Calendário Escolar"

        verbose_name_plural = "Calendário Escolar"

    # ======================================================
    # STRING
    # ======================================================

    def __str__(self):

        return (
            f"{self.titulo} | "
            f"{self.tipo} | "
            f"{self.data_inicio}"
        )

    # ======================================================
    # EVENTO TERMINADO
    # ======================================================

    @property
    def terminado(self):

        from django.utils import timezone

        hoje = timezone.now().date()

        if self.data_fim:

            return self.data_fim < hoje

        return self.data_inicio < hoje

    # ======================================================
    # EVENTO HOJE
    # ======================================================

    @property
    def acontecendo_hoje(self):

        from django.utils import timezone

        hoje = timezone.now().date()

        if self.data_fim:

            return self.data_inicio <= hoje <= self.data_fim

        return self.data_inicio == hoje


class MiniPauta(models.Model):

    TRIMESTRES = [
        ("1", "1º Trimestre"),
        ("2", "2º Trimestre"),
        ("3", "3º Trimestre"),
    ]

    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    ano_letivo = models.ForeignKey(AnoLetivo, on_delete=models.CASCADE)

    trimestre = models.CharField(max_length=1, choices=TRIMESTRES)

    # =========================
    # AVALIAÇÕES FIXAS (GRADEBOOK)
    # =========================
    av1 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    av2 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    av3 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    p1 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    av4 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    av5 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    av6 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    p2 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    exame = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    recurso = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    observacao = models.TextField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            "aluno",
            "turma",
            "disciplina",
            "ano_letivo",
            "trimestre",
        )
        ordering = ["aluno__numero_na_turma"]

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.disciplina.nome} - T{self.trimestre}"




class Notificacao(models.Model):

    TIPO_CHOICES = [
        ("danger", "Erro"),
        ("success", "Sucesso"),
        ("info", "Info"),
        ("warning", "Aviso"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="info")
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
