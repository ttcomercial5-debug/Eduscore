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
    nome_sistema = models.CharField(max_length=200, default="EdusCel")
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
        verbose_name="Identificador da Turma"
    )


    sala = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Sala"
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
        verbose_name="Professor Responsável"
    )

    diretor_turma = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={
            "role": "PROFESSOR"
        },
        related_name="turmas_como_diretor",
        verbose_name="Diretor de Turma"
    )


    criada_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )


    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'classe',
                    'identificador',
                    'turno',
                    'ano_letivo',
                    'escola',
                    'curso'
                ],
                name='unique_turma_por_curso'
            )
        ]

        verbose_name = "Turma"
        verbose_name_plural = "Turmas"


    def nome_completo(self):

        nome = (
            f"{self.get_classe_display()} "
            f"{self.identificador}"
        )

        if self.sala:
            nome += f" - Sala {self.sala}"

        nome += (
            f" - {self.get_turno_display()}"
            f" - {self.ano_letivo}"
        )

        return nome


    def __str__(self):

        return self.nome_completo()


    @staticmethod
    def ordenar_queryset(queryset):

        return queryset.annotate(
            classe_int=Cast(
                'classe',
                IntegerField()
            )
        ).order_by(
            'classe_int',
            'identificador'
        )




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
from decimal import Decimal


User = get_user_model()



class Pagamento(models.Model):


    # ======================================================
    # TIPOS DE PAGAMENTO
    # ======================================================


    TIPOS = [


        ("MENSALIDADE", "Mensalidade"),

        ("INSCRICAO", "Inscrição"),

        ("UNIFORME", "Uniforme"),

        ("EXAME", "Exame"),

        ("DECLARACAO", "Declaração"),

        ("MULTA", "Multa"),

        ("OUTRO", "Outro"),

    ]



    # ======================================================
    # ALUNO
    # ======================================================


    aluno = models.ForeignKey(

        "Aluno",

        on_delete=models.CASCADE,

        related_name="pagamentos",

        verbose_name="Aluno"

    )



    # ======================================================
    # ESCOLA
    # ======================================================


    escola = models.ForeignKey(

        "Escola",

        on_delete=models.CASCADE,

        related_name="pagamentos",

        verbose_name="Escola"

    )



    # ======================================================
    # MENSALIDADE RELACIONADA
    # ======================================================


    mensalidade = models.ForeignKey(

        "Mensalidade",

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="pagamentos",

        verbose_name="Mensalidade"

    )



    # ======================================================
    # ANO LETIVO
    # ======================================================


    ano_letivo = models.ForeignKey(

        "AnoLetivo",

        on_delete=models.CASCADE,

        related_name="pagamentos",

        verbose_name="Ano Letivo"

    )



    # ======================================================
    # TIPO
    # ======================================================


    tipo = models.CharField(

        max_length=30,

        choices=TIPOS,

        default="MENSALIDADE"

    )



    # ======================================================
    # VALOR BASE
    # ======================================================


    valor_pago = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        verbose_name="Valor Pago"

    )



    # ======================================================
    # MÉTODO DE PAGAMENTO
    # CONFIGURADO PELO FINANCEIRO
    # ======================================================


    forma_pagamento = models.ForeignKey(

        "MetodoPagamento",

        on_delete=models.PROTECT,

        related_name="pagamentos",

        verbose_name="Método de Pagamento"

    )



    # ======================================================
    # TAXA DO MÉTODO
    # Ex: TPA 2%
    # ======================================================


    taxa_percentual = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=0,

        verbose_name="Taxa (%)"

    )



    taxa_valor = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="Valor da Taxa"

    )



    # ======================================================
    # TOTAL RECEBIDO
    # ======================================================


    total_recebido = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="Total Recebido"

    )



    # ======================================================
    # RECIBO
    # ======================================================


    numero_recibo = models.CharField(

        max_length=40,

        unique=True,

        blank=True

    )



    # ======================================================
    # REFERÊNCIA
    # ======================================================


    referencia = models.CharField(

        max_length=100,

        blank=True,

        null=True

    )



    # ======================================================
    # OBSERVAÇÃO
    # ======================================================


    observacao = models.TextField(

        blank=True,

        null=True

    )



    # ======================================================
    # UTILIZADOR QUE RECEBEU
    # ======================================================


    recebido_por = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="pagamentos_recebidos"

    )



    # ======================================================
    # DATAS
    # ======================================================


    data_pagamento = models.DateTimeField(

        auto_now_add=True

    )


    criado_em = models.DateTimeField(

        auto_now_add=True

    )




    class Meta:


        ordering = [

            "-criado_em"

        ]


        indexes = [


            models.Index(

                fields=[

                    "escola",

                    "tipo"

                ]

            ),


            models.Index(

                fields=[

                    "aluno",

                    "criado_em"

                ]

            ),


            models.Index(

                fields=[

                    "numero_recibo"

                ]

            ),

        ]



    # ======================================================
    # GERAR NÚMERO RECIBO
    # ======================================================


    def gerar_numero_recibo(self):


        ano = "0000"



        if self.ano_letivo:


            try:

                ano = self.ano_letivo.nome.split("/")[-1]


            except:


                ano = self.ano_letivo.nome




        ultimo = Pagamento.objects.filter(

            escola=self.escola,

            numero_recibo__startswith=f"REC-{ano}"

        ).order_by(

            "-id"

        ).first()




        if not ultimo:


            return f"REC-{ano}-00001"




        try:


            numero = int(

                ultimo.numero_recibo.split("-")[-1]

            )


        except:


            numero = 0




        return (

            f"REC-{ano}-"

            f"{str(numero + 1).zfill(5)}"

        )




    # ======================================================
    # CALCULAR TAXA
    # ======================================================


    def calcular_taxa(self):


        if not self.forma_pagamento:

            return Decimal("0.00")



        if not self.forma_pagamento.cobra_taxa:


            return Decimal("0.00")



        percentual = Decimal(

            self.forma_pagamento.percentual_taxa

            or 0

        )



        return (

            self.valor_pago *

            percentual /

            Decimal("100")

        )




    # ======================================================
    # SAVE
    # ======================================================


    def save(self, *args, **kwargs):



        # escola automática

        if not self.escola and self.aluno:


            self.escola = self.aluno.escola




        # validar método da escola


        if self.forma_pagamento:


            if self.forma_pagamento.escola != self.escola:


                raise ValueError(

                    "Método de pagamento inválido para esta escola."

                )




        # ano letivo automático


        if not self.ano_letivo and self.escola:


            from .models import AnoLetivo



            ano = AnoLetivo.objects.filter(

                escola=self.escola,

                ativo=True

            ).first()



            if ano:

                self.ano_letivo = ano




        # calcular taxa


        self.taxa_percentual = (

            self.forma_pagamento.percentual_taxa

            if self.forma_pagamento

            else 0

        )



        self.taxa_valor = self.calcular_taxa()



        self.total_recebido = (

            self.valor_pago +

            self.taxa_valor

        )




        # gerar recibo


        if not self.numero_recibo:


            self.numero_recibo = (

                self.gerar_numero_recibo()

            )




        super().save(*args, **kwargs)




        # atualizar mensalidade


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

    ano_letivo = models.ForeignKey(
        "AnoLetivo",
        on_delete=models.CASCADE,
        related_name="horarios",
        verbose_name="Ano Letivo"
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

    bloqueado = models.BooleanField(
        default=False,
        verbose_name="Horário bloqueado"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = (
            "escola",
            "ano_letivo",
            "turma",
            "turno",
        )
        ordering = [
            "-ano_letivo__nome",
            "turma__classe",
            "turma__identificador",
        ]

    def __str__(self):
        return f"{self.turma} | {self.ano_letivo}"


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


from django.db import models


class ConfiguracaoFinanceira(models.Model):

    escola = models.OneToOneField(
        Escola,
        on_delete=models.CASCADE,
        related_name="configuracao_financeira"
    )

    # ======================================================
    # DADOS FINANCEIROS
    # ======================================================

    nif = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    endereco_financeiro = models.TextField(
        blank=True,
        null=True
    )

    telefone_financeiro = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    email_financeiro = models.EmailField(
        blank=True,
        null=True
    )

    moeda = models.CharField(
        max_length=10,
        default="Kz"
    )

    formato_valor = models.CharField(
        max_length=30,
        default="1.500,00 Kz"
    )

    responsavel_financeiro = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    telefone_responsavel = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    email_responsavel = models.EmailField(
        blank=True,
        null=True
    )

    ativo = models.BooleanField(
        default=True
    )

    # ======================================================
    # CONFIGURAÇÕES DE PAGAMENTO
    # ======================================================

    dia_vencimento = models.PositiveIntegerField(
        default=10,
        help_text="Dia padrão de vencimento das mensalidades."
    )

    permitir_pagamento_atrasado = models.BooleanField(
        default=True
    )

    # ======================================================
    # MULTAS E JUROS (PADRÃO)
    # ======================================================

    aplicar_multa_atraso = models.BooleanField(
        default=False
    )

    dias_tolerancia = models.PositiveIntegerField(
        default=5
    )

    valor_multa_mensalidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    percentual_juro_diario = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    percentual_desconto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # ======================================================
    # SERVIÇOS DA ESCOLA
    # ======================================================

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

    valor_certificado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_historico = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_transferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ======================================================
    # RECIBOS
    # ======================================================

    nome_recibo = models.CharField(
        max_length=100,
        default="Recibo"
    )

    prefixo_recibo = models.CharField(
        max_length=10,
        default="REC"
    )

    numero_inicial_recibo = models.PositiveIntegerField(
        default=1
    )

    mostrar_logo_recibo = models.BooleanField(
        default=True
    )

    mostrar_assinatura = models.BooleanField(
        default=True
    )

    mostrar_carimbo = models.BooleanField(
        default=True
    )

    texto_rodape_recibo = models.TextField(
        blank=True,
        null=True
    )

    # ======================================================
    # DADOS BANCÁRIOS
    # ======================================================

    banco = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    iban = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    numero_conta = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    titular_conta = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    swift = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # ======================================================
    # ALERTAS
    # ======================================================

    avisar_mensalidade_vencida = models.BooleanField(
        default=True
    )

    avisar_pagamento_recebido = models.BooleanField(
        default=True
    )

    avisar_despesa_alta = models.BooleanField(
        default=True
    )

    # ======================================================
    # RELATÓRIOS
    # ======================================================

    formato_relatorio = models.CharField(
        max_length=10,
        default="PDF"
    )

    mostrar_graficos = models.BooleanField(
        default=True
    )

    mostrar_comparacao = models.BooleanField(
        default=True
    )

    mostrar_saldo = models.BooleanField(
        default=True
    )

    # ======================================================
    # AUDITORIA
    # ======================================================

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    # ======================================================
    # MÉTODOS
    # ======================================================

    def calcular_multa(self):

        if not self.aplicar_multa_atraso:
            return 0

        return self.valor_multa_mensalidade

    @property
    def simbolo_moeda(self):
        return self.moeda or "Kz"

    def resumo(self):

        return {
            "escola": self.escola.nome,
            "moeda": self.moeda,
            "dia_vencimento": self.dia_vencimento,
            "multa": self.valor_multa_mensalidade,
            "juro": self.percentual_juro_diario,
            "desconto": self.percentual_desconto,
            "banco": self.banco,
        }

    def __str__(self):

        return (
            f"Configuração Financeira - "
            f"{self.escola.nome}"
        )


# ======================================================
# CONFIGURAÇÃO DE MENSALIDADES POR CLASSE
# ======================================================
from decimal import Decimal

from django.db import models
from django.db.models import Q

from academic.models import Escola



class ConfiguracaoMensalidade(models.Model):
    """
    Configuração financeira das mensalidades.

    Regras:

    Iniciação até 9ª Classe:
        Classe + Escola

    Exemplo:
        1ª Classe -> 10.000 Kz


    10ª até 13ª Classe:
        Classe + Curso + Escola

    Exemplo:

        10ª Classe
            Ciências Físicas -> 25.000 Kz

        10ª Classe
            Ciências Económicas -> 23.000 Kz
    """



    CLASSES = [

        ("0", "Iniciação"),

        ("1", "1ª Classe"),
        ("2", "2ª Classe"),
        ("3", "3ª Classe"),
        ("4", "4ª Classe"),
        ("5", "5ª Classe"),
        ("6", "6ª Classe"),

        ("7", "7ª Classe"),
        ("8", "8ª Classe"),
        ("9", "9ª Classe"),

        ("10", "10ª Classe"),
        ("11", "11ª Classe"),
        ("12", "12ª Classe"),
        ("13", "13ª Classe"),

    ]



    # ======================================================
    # ESCOLA
    # ======================================================


    escola = models.ForeignKey(

        Escola,

        on_delete=models.CASCADE,

        related_name="configuracoes_mensalidades"

    )



    # ======================================================
    # CURSO
    # OBRIGATÓRIO 10ª - 13ª
    # ======================================================


    curso = models.ForeignKey(

        "Curso",

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="configuracoes_mensalidades",

        verbose_name="Curso"

    )



    # ======================================================
    # CLASSE
    # ======================================================


    classe = models.CharField(

        max_length=10,

        choices=CLASSES,

        verbose_name="Classe"

    )



    ordem = models.PositiveIntegerField(

        default=0

    )



    # ======================================================
    # VALOR MENSALIDADE
    # ======================================================


    valor = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    # ======================================================
    # VENCIMENTO
    # ======================================================


    dia_vencimento = models.PositiveIntegerField(

        default=10

    )



    # ======================================================
    # MULTAS E JUROS
    # ======================================================


    aplicar_multa = models.BooleanField(

        default=False

    )


    dias_tolerancia = models.PositiveIntegerField(

        default=5

    )


    valor_multa = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )


    percentual_juros = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=0

    )


    percentual_desconto = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=0

    )



    # ======================================================
    # ESTADO
    # ======================================================


    ativo = models.BooleanField(

        default=True

    )



    observacao = models.TextField(

        blank=True,

        null=True

    )



    # ======================================================
    # AUDITORIA
    # ======================================================


    criado_em = models.DateTimeField(

        auto_now_add=True

    )


    atualizado_em = models.DateTimeField(

        auto_now=True

    )



    class Meta:


        verbose_name = (

            "Configuração de Mensalidade"

        )


        verbose_name_plural = (

            "Configurações de Mensalidades"

        )


        ordering = [

            "ordem",

            "classe",

            "curso__nome"

        ]



        constraints = [


            models.UniqueConstraint(

                fields=[

                    "escola",

                    "curso",

                    "classe"

                ],

                name=

                "unique_config_mensalidade_escola_curso_classe"

            )

        ]



    # ======================================================
    # VALIDAR CONFIGURAÇÃO
    # ======================================================


    def clean(self):


        classe = int(self.classe)



        # Até 9ª não permite curso

        if classe <= 9:


            self.curso = None



        # 10ª até 13ª exige curso

        if classe >= 10 and not self.curso:


            from django.core.exceptions import ValidationError


            raise ValidationError(

                "Da 10ª à 13ª classe é obrigatório selecionar o curso."

            )



    # ======================================================
    # SAVE
    # ======================================================


    def save(
        self,
        *args,
        **kwargs
    ):


        self.clean()


        super().save(
            *args,
            **kwargs
        )



    # ======================================================
    # OBTER VALOR
    # ======================================================


    @classmethod
    def obter_valor(

        cls,

        escola,

        classe,

        curso=None

    ):


        configuracao = cls.objects.filter(

            escola=escola,

            classe=classe,

            curso=curso,

            ativo=True

        ).first()



        if configuracao:

            return configuracao.valor



        # fallback para classe geral

        if curso:


            configuracao = cls.objects.filter(

                escola=escola,

                classe=classe,

                curso__isnull=True,

                ativo=True

            ).first()



            if configuracao:

                return configuracao.valor



        return Decimal("0.00")



    # ======================================================
    # OBTER CONFIGURAÇÃO COMPLETA
    # ======================================================


    @classmethod
    def obter_configuracao(

        cls,

        escola,

        classe,

        curso=None

    ):


        configuracao = cls.objects.filter(

            escola=escola,

            classe=classe,

            curso=curso,

            ativo=True

        ).first()



        if configuracao:

            return configuracao



        if curso:


            return cls.objects.filter(

                escola=escola,

                classe=classe,

                curso__isnull=True,

                ativo=True

            ).first()



        return None



    # ======================================================
    # ATUALIZAR MENSALIDADES PENDENTES
    # ======================================================


    def atualizar_mensalidades(self):


        from .models import Mensalidade



        mensalidades = Mensalidade.objects.filter(

            aluno__escola=self.escola,

            aluno__turma__classe=self.classe,

            status="PENDENTE"

        )



        if self.curso:


            mensalidades = mensalidades.filter(

                aluno__turma__curso=self.curso

            )



        quantidade = mensalidades.update(

            valor=self.valor

        )



        return quantidade



    # ======================================================
    # RESUMO
    # ======================================================


    def resumo(self):


        return {


            "classe":

                self.get_classe_display(),



            "curso":

                self.curso.nome

                if self.curso

                else "Sem curso",



            "valor":

                self.valor,



            "vencimento":

                self.dia_vencimento,



            "ativo":

                self.ativo

        }



    # ======================================================
    # STRING
    # ======================================================


    def __str__(self):


        moeda = "Kz"



        if hasattr(
            self.escola,
            "configuracao_financeira"
        ):


            moeda = (

                self.escola

                .configuracao_financeira

                .moeda

            )



        texto = (

            f"{self.get_classe_display()}"

        )



        if self.curso:


            texto += (

                f" - {self.curso.nome}"

            )



        return (

            f"{texto} | "

            f"{self.valor} {moeda}"

        )


class Curso(models.Model):

    nome = models.CharField(
        max_length=90,
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

    coordenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cursos_coordenados",
        limit_choices_to={"role": "PROFESSOR"},
        verbose_name="Coordenador do Curso",
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:

        verbose_name = "Curso"

        verbose_name_plural = "Cursos"

        unique_together = (
            "nome",
            "escola",
        )


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


class ConfiguracaoMultaJuros(models.Model):

    escola = models.OneToOneField(
        Escola,
        on_delete=models.CASCADE,
        related_name="configuracao_multa_juros"
    )


    aplicar_multa = models.BooleanField(
        default=False
    )


    TIPO_MULTA = [

        ("FIXA","Valor Fixo"),

        ("PERCENTUAL","Percentual")

    ]


    tipo_multa = models.CharField(
        max_length=20,
        choices=TIPO_MULTA,
        default="FIXA"
    )


    valor_multa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )


    dias_tolerancia = models.PositiveIntegerField(
        default=5
    )


    percentual_juros = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )


    ativo = models.BooleanField(
        default=True
    )


    atualizado_em = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return f"Multas e Juros - {self.escola.nome}"


# ============================================================
# MÉTODOS DE PAGAMENTO
# EDUSCEL - ICA SYSTEMS
# ============================================================

from django.db import models


class MetodoPagamento(models.Model):
    """
    Métodos de pagamento disponíveis para cada escola.

    Exemplos:
    - Dinheiro
    - Transferência Bancária
    - Multicaixa Express
    - TPA
    - Cheque
    - Unitel Money
    """

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="metodos_pagamento",
        verbose_name="Escola",
    )

    nome = models.CharField(
        max_length=100,
        verbose_name="Nome"
    )

    codigo = models.CharField(
        max_length=50,
        verbose_name="Código"
    )

    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )

    metodo_padrao = models.BooleanField(
        default=False,
        verbose_name="Método padrão"
    )

    exige_comprovativo = models.BooleanField(
        default=False,
        verbose_name="Exigir comprovativo"
    )

    permite_pagamento_parcial = models.BooleanField(
        default=True,
        verbose_name="Permitir pagamento parcial"
    )

    permite_troco = models.BooleanField(
        default=False,
        verbose_name="Permitir troco"
    )

    cobra_taxa = models.BooleanField(
        default=False,
        verbose_name="Cobrar taxa"
    )

    percentual_taxa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Percentual da taxa (%)"
    )

    ordem = models.PositiveIntegerField(
        default=1,
        verbose_name="Ordem de exibição"
    )

    cor = models.CharField(
        max_length=20,
        default="#2563eb",
        verbose_name="Cor"
    )

    icone = models.CharField(
        max_length=50,
        default="bi-credit-card",
        verbose_name="Ícone Bootstrap"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Método de Pagamento"
        verbose_name_plural = "Métodos de Pagamento"
        ordering = [
            "ordem",
            "nome"
        ]
        unique_together = [
            "escola",
            "codigo"
        ]

    def __str__(self):
        return f"{self.nome} ({self.escola.nome})"

    def save(self, *args, **kwargs):
        """
        Garante apenas um método padrão por escola.
        """
        super().save(*args, **kwargs)

        if self.metodo_padrao:
            MetodoPagamento.objects.filter(
                escola=self.escola
            ).exclude(
                pk=self.pk
            ).update(
                metodo_padrao=False
            )


# ============================================================
# DADOS BANCÁRIOS
# ============================================================

class ContaBancaria(models.Model):
    """
    Contas bancárias utilizadas pela escola.

    Podem ser usadas por:
    - Transferência Bancária
    - TPA
    - Multicaixa Express
    """

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="contas_bancarias",
        verbose_name="Escola"
    )

    banco = models.CharField(
        max_length=150,
        verbose_name="Banco"
    )

    titular = models.CharField(
        max_length=200,
        verbose_name="Titular"
    )

    numero_conta = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Número da Conta"
    )

    iban = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="IBAN"
    )

    swift = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="SWIFT"
    )

    numero_telefone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefone associado"
    )

    qr_code = models.ImageField(
        upload_to="financeiro/qr_codes/",
        blank=True,
        null=True,
        verbose_name="QR Code"
    )

    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Conta Bancária"
        verbose_name_plural = "Contas Bancárias"
        ordering = [
            "banco",
            "titular"
        ]

    def __str__(self):
        return f"{self.banco} - {self.titular}"


# ============================================================
# MÉTODOS PADRÃO DO SISTEMA
# ============================================================

METODOS_PADRAO = [
    ("DINHEIRO", "Dinheiro"),
    ("TRANSFERENCIA", "Transferência Bancária"),
    ("MULTICAIXA_EXPRESS", "Multicaixa Express"),
    ("TPA", "TPA"),
    ("CHEQUE", "Cheque"),
    ("UNITEL_MONEY", "Unitel Money"),
    ("AFRIMONEY", "Afrimoney"),
    ("EKWANZA", "e-Kwanza"),
    ("OUTRO", "Outro"),
]