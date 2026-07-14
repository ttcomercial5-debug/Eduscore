from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from academic.models import  HistoricoMatricula, CalendarioEscolar, Entrada, FechamentoTrimestre, Trimestre, Escola, Despesa, Configuracao, PagamentoPlano, Plano, Curso, Aluno, Pagamento,  Turma, Nota, Professor, Disciplina, AnoLetivo, Horario, Mensalidade, Boletim, Frequencia, HistoricoAcademico, HorarioTurma, AulaHorario, ConfiguracaoFinanceira
from finance.models import  MovimentoCaixa
from django.db.models import Count, Avg, Sum
from openpyxl.drawing import Drawing
from users.models import User
from decimal import Decimal
from academic.forms import DisciplinaForm, AlunoForm, ConfiguracaoForm, CalendarioEscolarForm
from django.db import transaction
from django.db.models import Prefetch
from django.contrib import messages
from django.contrib.auth.hashers import check_password
import json
from django.http import JsonResponse
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.urls import reverse
from datetime import date, datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from finance.utils import gerar_mensalidades_aluno
import random
import string
import qrcode
from io import BytesIO




User = get_user_model()


# =====================================================
# TER A ESCOLA ATIVA
# =====================================================

def get_escola(request):
    """
    SUPERADMIN usa escola da sessão.
    Outros usuários usam a escola vinculada.
    """

    user = request.user

    # SUPERADMIN escolhe escola manualmente
    if user.role == 'SUPERADMIN':
        escola_id = request.session.get('escola_id')
        if escola_id:
            return Escola.objects.filter(id=escola_id).first()
        return None

    # Outros usuários usam a escola vinculada
    return user.escola


# =====================================================
# LOGIN
# =====================================================

def login_view(request):
    error = None

    # Se já estiver logado
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == "POST":

        codigo_escola = request.POST.get("codigo_escola")
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Campos obrigatórios
        if not username or not password:
            error = "Preencha todos os campos."
            return render(request, "login.html", {"error": error})

        # Verificar se o utilizador existe
        try:
            utilizador = User.objects.get(username=username)

            # Conta bloqueada?
            if (
                utilizador.bloqueado_ate
                and utilizador.bloqueado_ate > timezone.now()
            ):
                minutos = max(
                    1,
                    int(
                        (
                            utilizador.bloqueado_ate
                            - timezone.now()
                        ).total_seconds() / 60
                    )
                )

                error = (
                    f"Conta bloqueada. "
                    f"Tente novamente em {minutos} minuto(s)."
                )

                return render(
                    request,
                    "login.html",
                    {"error": error}
                )

        except User.DoesNotExist:
            utilizador = None

        # Autenticar
        user = authenticate(
            request,
            username=username,
            password=password
        )

        # Senha errada
        if user is None:

            if utilizador:

                utilizador.tentativas_login += 1

                if utilizador.tentativas_login >= 3:

                    utilizador.bloqueado_ate = (
                        timezone.now()
                        + timedelta(minutes=15)
                    )

                    utilizador.save()

                    error = (
                        "Conta bloqueada por 15 minutos devido "
                        "a várias tentativas inválidas."
                    )

                else:

                    restantes = (
                        3 - utilizador.tentativas_login
                    )

                    utilizador.save()

                    error = (
                        f"Credenciais inválidas. "
                        f"Restam {restantes} tentativa(s)."
                    )

            else:
                error = "Usuário ou senha inválidos."

            return render(
                request,
                "login.html",
                {"error": error}
            )

        # Resetar contador após login correto
        user.tentativas_login = 0
        user.bloqueado_ate = None
        user.save()

        # SUPERADMIN
        if user.is_superuser:

            login(request, user)

            return redirect_user_by_role(user)

        # Código escola obrigatório
        if not codigo_escola:

            error = "Preencha o Código da Escola."

            return render(
                request,
                "login.html",
                {"error": error}
            )

        # Buscar escola
        try:

            escola = Escola.objects.get(
                codigo=codigo_escola
            )

        except Escola.DoesNotExist:

            error = "Código da escola inválido."

            return render(
                request,
                "login.html",
                {"error": error}
            )

        # Verificar escola do utilizador
        if (
            not user.escola
            or str(user.escola.codigo)
            != str(codigo_escola)
        ):

            error = (
                "Usuário não pertence a esta escola."
            )

            return render(
                request,
                "login.html",
                {"error": error}
            )

        # Utilizador ativo
        if not user.ativo:

            error = "Usuário bloqueado."

            return render(
                request,
                "login.html",
                {"error": error}
            )

        # Login
        login(request, user)

        request.session["escola_id"] = (
            user.escola.id
        )

        return redirect_user_by_role(user)

    return render(
        request,
        "login.html",
        {"error": error}
    )




#==================================================
#   RECUPERAR SENHA
#==================================================
import random

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone

import secrets

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone

from academic.models import Escola

from core.service.sms_service import enviar_sms



User = get_user_model()




def esqueci_senha(request):


    if request.method == "POST":


        codigo_escola = request.POST.get(
            "codigo_escola",
            ""
        ).strip()


        username = request.POST.get(
            "username",
            ""
        ).strip()


        telefone = request.POST.get(
            "telefone",
            ""
        ).strip()



        # =====================================
        # VALIDAÇÕES INICIAIS
        # =====================================


        if not username:


            messages.error(
                request,
                "Informe o nome de utilizador."
            )


            return render(
                request,
                "recuperar_senha.html"
            )



        if not telefone:


            messages.error(
                request,
                "Informe o telefone associado à conta."
            )


            return render(
                request,
                "recuperar_senha.html"
            )





        user = None




        # =====================================
        # SUPERADMIN
        # =====================================


        try:


            user = User.objects.get(
                username=username,
                is_superuser=True
            )


            # Confirma telefone do superadmin

            if user.telefone != telefone:

                user = None



        except User.DoesNotExist:


            user = None





        # =====================================
        # UTILIZADORES NORMAIS
        # =====================================


        if not user:



            if not codigo_escola:


                messages.error(
                    request,
                    "Informe o código da escola."
                )


                return render(
                    request,
                    "recuperar_senha.html"
                )




            try:


                escola = Escola.objects.get(
                    codigo=codigo_escola
                )


            except Escola.DoesNotExist:


                messages.error(
                    request,
                    "Dados inválidos."
                )


                return render(
                    request,
                    "recuperar_senha.html"
                )





            try:


                user = User.objects.get(
                    username=username,
                    telefone=telefone,
                    escola=escola
                )


            except User.DoesNotExist:



                messages.error(
                    request,
                    "Dados inválidos."
                )


                return render(
                    request,
                    "recuperar_senha.html"
                )






        # =====================================
        # GERAR OTP SEGURO
        # =====================================


        otp = str(
            secrets.randbelow(900000) + 100000
        )



        expiracao = (
            timezone.now()
            +
            timedelta(minutes=5)
        )



        user.otp_codigo = otp

        user.otp_expira_em = expiracao



        user.save(
            update_fields=[
                "otp_codigo",
                "otp_expira_em"
            ]
        )





        # =====================================
        # ENVIO SMS
        # =====================================


        mensagem = (

            f"EdusCel: Seu código de recuperação "
            f"é {otp}. "
            "Válido por 5 minutos."

        )



        enviado = enviar_sms(
            user.telefone,
            mensagem
        )




        if not enviado:



            messages.error(
                request,
                "Não foi possível enviar o código."
            )


            return render(
                request,
                "recuperar_senha.html"
            )





        # =====================================
        # SUCESSO
        # =====================================


        messages.success(
            request,
            "Código OTP enviado para o telefone associado."
        )



        return render(
            request,
            "recuperar_senha.html"
        )





    return render(
        request,
        "recuperar_senha.html"
    )



from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone


User = get_user_model()



def confirmar_otp_recuperacao(request):

    if request.method == "POST":


        username = request.POST.get(
            "username",
            ""
        ).strip()


        otp_codigo = request.POST.get(
            "otp_codigo",
            ""
        ).strip()


        nova_senha = request.POST.get(
            "nova_senha",
            ""
        ).strip()


        confirmar_senha = request.POST.get(
            "confirmar_senha",
            ""
        ).strip()



        # =====================================
        # VALIDAÇÕES INICIAIS
        # =====================================


        if not username:

            messages.error(
                request,
                "Informe o nome de utilizador."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if not otp_codigo:

            messages.error(
                request,
                "Informe o código OTP recebido."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if not nova_senha or not confirmar_senha:

            messages.error(
                request,
                "Informe e confirme a nova senha."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if nova_senha != confirmar_senha:

            messages.error(
                request,
                "As senhas não coincidem."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if len(nova_senha) < 6:

            messages.error(
                request,
                "A senha deve possuir pelo menos 6 caracteres."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        # =====================================
        # BUSCAR UTILIZADOR
        # =====================================


        try:

            user = User.objects.get(
                username=username
            )


        except User.DoesNotExist:


            messages.error(
                request,
                "Utilizador não encontrado."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        # =====================================
        # VALIDAR OTP
        # =====================================


        if not user.otp_codigo:

            messages.error(
                request,
                "Nenhum código OTP solicitado."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if user.otp_codigo != otp_codigo:

            messages.error(
                request,
                "Código OTP inválido."
            )

            return redirect(
                "confirmar_otp_recuperacao"
            )



        if (
            user.otp_expira_em
            and
            timezone.now() > user.otp_expira_em
        ):

            messages.error(
                request,
                "O código OTP expirou. Solicite um novo código."
            )

            user.otp_codigo = None
            user.otp_expira_em = None

            user.save(
                update_fields=[
                    "otp_codigo",
                    "otp_expira_em"
                ]
            )

            return redirect(
                "esqueci_senha"
            )



        # =====================================
        # ALTERAR SENHA
        # =====================================


        user.set_password(
            nova_senha
        )


        # Limpar OTP após utilização

        user.otp_codigo = None

        user.otp_expira_em = None


        user.save()



        messages.success(
            request,
            "Senha alterada com sucesso. Já pode iniciar sessão."
        )


        return redirect(
            "login"
        )



    return render(
        request,
        "confirmar_otp_recuperacao.html"
    )

# ==================================================
#  Função centralizada de redirecionamento
# ==================================================
def redirect_user_by_role(user):



    if user.role == 'SUPERADMIN':
        return redirect('escolas')

    if user.role == 'DIRETOR':
        return redirect('dashboard')

    if user.role == 'DIRETOR_PEDAGOGICO':
        return redirect('dashboard_diretor_pedagogico')

    if user.role == 'PROFESSOR':
        return redirect('dashboard_professor')

    if user.role == 'SECRETARIA':
        return redirect('dashboard_secretaria')

    if user.role == 'FINANCEIRO':
        return redirect('dashboard_financeiro')

    if user.role == 'ALUNO':
        return redirect('dashboard_aluno')

    return redirect('login')


# =====================================================
# LOGOUT
# =====================================================

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')


# =====================================================
# DASHBOARD
# =====================================================

from decimal import Decimal
from django.db.models import Sum, Avg, Count, Q
from collections import defaultdict

@login_required
def dashboard(request):

    # =================================================
    # PERMISSÃO
    # =================================================

    if request.user.role not in ["DIRETOR", "SUPERADMIN"]:
        return redirect("bloqueado")

    escola = get_escola(request)

    if not escola:

        if request.user.role == "SUPERADMIN":
            return redirect("escolas")

        return redirect("login")

    # =================================================
    # ANO LETIVO ATIVO
    # =================================================

    ano = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # =================================================
    # CONTADORES GERAIS
    # =================================================

    total_alunos = Aluno.objects.filter(
        escola=escola
    ).count()

    total_professores = User.objects.filter(
        role='PROFESSOR',
        escola=escola
    ).count()

    total_turmas = Turma.objects.filter(
        escola=escola
    ).count()

    total_recebido = Pagamento.objects.filter(
        aluno__escola=escola
    ).aggregate(
        total=Sum('valor_pago')
    )['total'] or Decimal("0.00")

    # =================================================
    # DASHBOARD AVANÇADO
    # =================================================

    aprovados = 0
    reprovados = 0
    percentagem_aprovacao = 0

    melhor_turma = None
    pior_disciplina = None

    evolucao = []

    alertas = []

    if ano:

        # =============================================
        # TAXA DE APROVAÇÃO
        # =============================================

        aprovados = Aluno.objects.filter(
            escola=escola,
            ano_letivo=ano,
            aprovado=True
        ).count()

        reprovados = Aluno.objects.filter(
            escola=escola,
            ano_letivo=ano,
            aprovado=False
        ).count()

        total_resultados = aprovados + reprovados

        if total_resultados > 0:

            percentagem_aprovacao = round(
                (aprovados / total_resultados) * 100,
                1
            )

        # =============================================
        # MELHOR TURMA
        # =============================================

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano
        )

        melhor_media = 0

        for turma in turmas:

            alunos_turma = Aluno.objects.filter(
                turma=turma
            )

            medias = [
                float(al.media_final)
                for al in alunos_turma
                if al.media_final is not None
            ]

            if medias:

                media_turma = round(
                    sum(medias) / len(medias),
                    1
                )

                if media_turma > melhor_media:

                    melhor_media = media_turma

                    melhor_turma = {
                        "nome": f"{turma.classe}ª {turma.identificador}",
                        "media": media_turma
                    }

        # =============================================
        # PIOR DISCIPLINA
        # =============================================

        disciplinas = Disciplina.objects.filter(
            escola=escola
        )

        pior_media = 999

        for disciplina in disciplinas:

            notas = Nota.objects.filter(
                disciplina=disciplina,
                ano_letivo=ano
            )

            medias = [
                float(n.media_final)
                for n in notas
                if n.media_final is not None
            ]

            if medias:

                media_disc = round(
                    sum(medias) / len(medias),
                    1
                )

                if media_disc < pior_media:

                    pior_media = media_disc

                    negativas = len([
                        n for n in medias
                        if n < 10
                    ])

                    pior_disciplina = {
                        "nome": disciplina.nome,
                        "media": media_disc,
                        "negativas": negativas
                    }

        # =============================================
        # EVOLUÇÃO ESCOLAR
        # =============================================

        for trimestre in [1, 2, 3]:

            notas_trim = Nota.objects.filter(
                escola=escola,
                ano_letivo=ano,
                trimestre=trimestre
            )

            medias_trim = [
                float(n.media_final)
                for n in notas_trim
                if n.media_final is not None
            ]

            media_trim = 0

            if medias_trim:

                media_trim = round(
                    sum(medias_trim) / len(medias_trim),
                    1
                )

            evolucao.append({
                "trimestre": f"{trimestre}º Trimestre",
                "media": media_trim
            })

        # =============================================
        # ALERTAS AUTOMÁTICOS
        # =============================================

        # TURMAS EM RISCO

        for turma in turmas:

            alunos_turma = Aluno.objects.filter(
                turma=turma
            )

            total_negativos = alunos_turma.filter(
                aprovado=False
            ).count()

            total_alunos_turma = alunos_turma.count()

            if total_alunos_turma > 0:

                taxa_negativa = (
                    total_negativos / total_alunos_turma
                ) * 100

                if taxa_negativa >= 40:

                    alertas.append(
                        f" Turma {turma.classe}ª {turma.identificador} está em risco."
                    )

        # DISCIPLINAS CRÍTICAS

        if pior_disciplina and pior_disciplina["media"] < 10:

            alertas.append(
                f" Disciplina crítica: {pior_disciplina['nome']}."
            )

        from django.utils import timezone

        hoje = timezone.now().date()

        # =================================================
        # PROFESSORES SEM LANÇAR NOTAS (BASEADO NO CALENDÁRIO)
        # =================================================

        provas_expiradas = CalendarioEscolar.objects.filter(
            escola=escola,
            ano_letivo=ano,
            tipo="PROVA",
            data_fim__lt=hoje
        )

        for prova in provas_expiradas:

            disciplinas_prova = Disciplina.objects.filter(
                escola=escola,
                ano_letivo=ano
            )

            for disciplina in disciplinas_prova:

                if Nota.objects.filter(
                        disciplina=disciplina,
                        ano_letivo=ano
                ).exists():
                    continue

                professor = disciplina.professor

                if professor:
                    alertas.append(
                        f" Professor {professor.get_full_name() or professor.username} não lançou notas da prova '{prova.titulo}'."
                    )

    # =================================================
    # BOTÃO PROMOÇÃO
    # =================================================

    mostrar_botao_promocao = False

    if ano:

        existe_p2_terceiro = Nota.objects.filter(
            aluno__escola=escola,
            ano_letivo=ano,
            trimestre=3,
            p2__isnull=False
        ).exists()

        if existe_p2_terceiro:
            mostrar_botao_promocao = True

    # =================================================
    # PRÓXIMO ANO
    # =================================================

    proximo_ano = None

    if ano:

        try:

            inicio, fim = ano.nome.split("/")

            proximo_ano = f"{int(inicio)+1}/{int(fim)+1}"

        except:
            proximo_ano = "Novo Ano"

    # =================================================
    # CONTEXT
    # =================================================

    context = {

        "ano": ano,
        "escola": escola,

        "total_alunos": total_alunos,
        "total_professores": total_professores,
        "total_turmas": total_turmas,
        "total_recebido": total_recebido,

        "mostrar_botao_promocao": mostrar_botao_promocao,

        # DASHBOARD AVANÇADO

        "aprovados": aprovados,
        "reprovados": reprovados,
        "percentagem_aprovacao": percentagem_aprovacao,

        "melhor_turma": melhor_turma,
        "pior_disciplina": pior_disciplina,

        "evolucao": evolucao,

        "alertas": alertas,

        "proximo_ano": proximo_ano,
    }

    return render(
        request,
        'dashboard.html',
        context
    )




# =====================================================
# ALUNOS
# =====================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.db.models import Q


@login_required
def lista_alunos(request):

    escola = get_escola(request)

    if not escola:
        return redirect("escolas")

    user = request.user

    # ======================================================
    # BASE TEMPLATE DINÂMICO (SISTEMA SaaS)
    # ======================================================
    if user.role == "DIRETOR_PEDAGOGICO":
        base_template = "base_diretor_pedagogico.html"

    elif user.role == "DIRETOR":
        base_template = "base.html"

    elif user.role == "PROFESSOR":
        base_template = "base_professor.html"

    else:
        return redirect("dashboard")

    # ======================================================
    # QUERY BASE
    # ======================================================
    alunos = (
        Aluno.objects
        .filter(escola=escola)
        .select_related(
            "usuario",
            "turma",
            "turma__curso",
            "ano_letivo"
        )
    )

    # ======================================================
    # PERMISSÕES
    # ======================================================
    if user.role == "PROFESSOR":
        alunos = alunos.filter(
            turma__professores__usuario=user
        )

    # ======================================================
    # ESTATÍSTICAS
    # ======================================================
    total_alunos = alunos.count()

    alunos_ativos = alunos.filter(
        usuario__is_active=True
    ).count()

    alunos_bloqueados = alunos.filter(
        usuario__is_active=False
    ).count()

    alunos_sem_turma = alunos.filter(
        turma__isnull=True
    ).count()

    total_turmas = (
        alunos.exclude(turma__isnull=True)
        .values("turma")
        .distinct()
        .count()
    )

    # ======================================================
    # BUSCA
    # ======================================================
    buscar = request.GET.get("buscar")

    if buscar:
        alunos = alunos.filter(
            Q(usuario__first_name__icontains=buscar) |
            Q(usuario__last_name__icontains=buscar) |
            Q(numero_bi__icontains=buscar) |
            Q(numero_processo__icontains=buscar)
        )

    # ======================================================
    # FILTRO TURMA
    # ======================================================
    turma_id = request.GET.get("turma")

    if turma_id:
        alunos = alunos.filter(turma_id=turma_id)

    # ======================================================
    # ORDER + PAGINAÇÃO
    # ======================================================
    alunos = alunos.order_by(
        Lower("usuario__first_name")
    )

    paginator = Paginator(alunos, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ======================================================
    # TURMAS
    # ======================================================
    if user.role == "PROFESSOR":

        turmas = (
            Turma.objects
            .filter(
                professores__usuario=user,
                escola=escola
            )
            .distinct()
            .order_by("classe", "identificador")
        )

    else:

        turmas = (
            Turma.objects
            .filter(escola=escola)
            .order_by("classe", "identificador")
        )

    # ======================================================
    # CONTEXTO
    # ======================================================
    return render(request, "alunos.html", {
        "alunos": page_obj,
        "turmas": turmas,
        "buscar": buscar,
        "turma_id": turma_id,

        "total_alunos": total_alunos,
        "alunos_ativos": alunos_ativos,
        "alunos_bloqueados": alunos_bloqueados,
        "alunos_sem_turma": alunos_sem_turma,
        "total_turmas": total_turmas,

        "base_template": base_template,
    })



# =====================================================
# PROFESSORES
# =====================================================
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.shortcuts import render, redirect



@login_required
def lista_professores(request):

    # ======================================================
    # PERMISSÃO (DIRETOR + DIRETOR_PEDAGOGICO)
    # ======================================================
    if request.user.role not in ["DIRETOR", "DIRETOR_PEDAGOGICO"]:
        return redirect("dashboard")

    escola = get_escola(request)

    if not escola:
        return redirect("dashboard")

    # ======================================================
    # BASE TEMPLATE DINÂMICO
    # ======================================================
    if request.user.role == "DIRETOR_PEDAGOGICO":
        base_template = "base_diretor_pedagogico.html"
    elif request.user.role == "DIRETOR":
        base_template = "base.html"
    else:
        base_template = "base.html"

    # ======================================================
    # QUERY PROFESSORES
    # ======================================================
    professores = User.objects.filter(
        role="PROFESSOR",
        escola=escola
    ).prefetch_related(
        Prefetch(
            "disciplinas",
            queryset=Disciplina.objects.select_related(
                "turma",
                "turma__curso"
            )
        )
    ).annotate(
        total_turmas=Count("disciplinas__turma", distinct=True),
        total_disciplinas=Count("disciplinas", distinct=True),
    ).order_by(
        "first_name",
        "username"
    )

    total_professores = professores.count()

    # ======================================================
    # CONTEXTO
    # ======================================================
    return render(request, "professores.html", {
        "professores": professores,
        "total_professores": total_professores,
        "base_template": base_template,
    })


# =====================================================
# TURMAS
# =====================================================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count



@login_required
def lista_turmas(request):

    escola = get_escola(request)

    if not escola:
        return redirect("escolas")

    user = request.user

    # =====================================================
    # BASE TEMPLATE DINÂMICO
    # =====================================================
    if user.role == "DIRETOR_PEDAGOGICO":
        base_template = "base_diretor_pedagogico.html"
    elif user.role == "DIRETOR":
        base_template = "base.html"
    elif user.role == "PROFESSOR":
        base_template = "base_professor.html"
    else:
        base_template = "base.html"

    # =====================================
    # Filtro por ano letivo
    # =====================================
    ano_id = request.GET.get("ano")

    anos_letivos = AnoLetivo.objects.filter(
        escola=escola
    ).order_by("-id")

    if ano_id:

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo_id=ano_id
        )

        ano_selecionado = AnoLetivo.objects.filter(
            id=ano_id,
            escola=escola
        ).first()

    else:

        ano_selecionado = AnoLetivo.objects.filter(
            escola=escola,
            ativo=True
        ).first()

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano_selecionado
        )

    # =====================================
    # PERMISSÃO POR ROLE
    # =====================================
    if user.role == "PROFESSOR":

        turmas = turmas.filter(
            professores__usuario=user
        )

    elif user.role not in ["DIRETOR", "DIRETOR_PEDAGOGICO"]:
        return redirect("dashboard")

    # =====================================
    # ESTATÍSTICAS
    # =====================================
    turmas = (
        turmas
        .select_related(
            "curso",
            "ano_letivo"
        )
        .annotate(
            total_alunos=Count("alunos")
        )
        .order_by(
            "classe",
            "identificador"
        )
    )

    # =====================================
    # CONTEXTO
    # =====================================
    return render(request, "turmas.html", {
        "turmas": turmas,
        "anos_letivos": anos_letivos,
        "ano_selecionado": ano_selecionado,
        "base_template": base_template,
    })




# =====================================================
# NOTAS
# =====================================================



@login_required
def lista_notas(request):
    # =========================
    # 1. Buscar escola do usuário
    # =========================
    escola = get_escola(request)
    if not escola:
        return redirect('dashboard')

    # =========================
    # 2. Buscar todas as notas da escola
    # =========================
    notas = Nota.objects.select_related(
        'aluno', 'turma', 'disciplina', 'professor'
    ).filter(aluno__escola=escola).order_by('aluno__nome', 'disciplina__nome', 'trimestre')

    # =========================
    # 3. Enviar para o template
    # =========================
    context = {
        'notas': notas
    }

    return render(request, 'notas.html', context)


# =====================================================
# SECRETARIA
# =====================================================

@login_required
def secretaria(request):

    escola = get_escola(request)
    if not escola:
        return redirect('dashboard')

    pagamentos = Pagamento.objects.filter(aluno__escola=escola)

    return render(request, 'secretaria.html', {
        'pagamentos': pagamentos
    })


# =====================================================
# ESCOLAS (APENAS SUPERADMIN) ELIMINAR ESCOLAS
# =====================================================

@login_required
def eliminar_escola(request, escola_id):
    # Apenas SUPERADMIN pode deletar escolas
    if request.user.role != 'SUPERADMIN':
        messages.error(request, "Você não tem permissão para eliminar escolas.")
        return redirect('lista_escolas')

    escola = get_object_or_404(Escola, id=escola_id)

    if request.method == "POST":
        escola.delete()
        messages.success(request, f"Escola '{escola.nome}' foi eliminada com sucesso.")
        return redirect('lista_escolas')

    # Caso alguém tente acessar via GET
    messages.warning(request, "Operação inválida. A exclusão deve ser feita via formulário.")
    return redirect('lista_escolas')

# =========================================
# Lista todas as escolas (visível apenas para SUPERADMIN)
# =========================================
@login_required
def lista_escolas(request):
    # Restrição de acesso
    if request.user.role != 'SUPERADMIN':
        return redirect('dashboard')

    # Pega todas as escolas ordenadas pelo nome
    escolas = Escola.objects.all()

    context = {
        'escolas': escolas,
    }

    return render(request, 'escolas.html', context)


# =========================================
# Seleciona uma escola e salva na sessão (visível apenas para SUPERADMIN)
# =========================================
@login_required
def selecionar_escola(request, escola_id):

    if request.user.role != 'SUPERADMIN':
        return redirect('dashboard')

    # Busca a escola ou retorna 404
    escola = get_object_or_404(Escola, id=escola_id)

    # Salva o ID da escola na sessão do usuário
    request.session['escola_id'] = escola.id


    return redirect('dashboard')





@login_required
@transaction.atomic
def adicionar_professor(request):

    if getattr(request.user, "role", None) != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    if not request.user.escola:
        messages.error(
            request,
            "O utilizador não está associado a nenhuma escola."
        )
        return redirect("dashboard")

    escola = request.user.escola

    turmas = (
        Turma.objects.filter(escola=escola)
        .order_by("classe", "identificador")
    )

    if request.method == "POST":

        # ==========================
        # DADOS PESSOAIS
        # ==========================

        nome_completo = request.POST.get(
            "nome_completo", ""
        ).strip()

        username = request.POST.get(
            "username", ""
        ).strip()

        email = request.POST.get(
            "email", ""
        ).strip().lower()

        telefone = request.POST.get(
            "telefone", ""
        ).strip()

        password = request.POST.get(
            "password", ""
        ).strip()

        # ==========================
        # DADOS ACADÉMICOS
        # ==========================

        disciplina = request.POST.get(
            "disciplina", ""
        ).strip()

        classes = request.POST.get(
            "classes", ""
        ).strip()

        turmas_ids = request.POST.getlist(
            "turmas"
        )

        # ==========================
        # VALIDAÇÕES
        # ==========================

        if not all([
            nome_completo,
            username,
            telefone,
            password,
            disciplina,
            classes,
        ]):

            messages.error(
                request,
                "Preencha todos os campos obrigatórios."
            )

            return redirect(
                "adicionar_professor"
            )

        if not turmas_ids:

            messages.error(
                request,
                "Selecione pelo menos uma turma."
            )

            return redirect(
                "adicionar_professor"
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Este nome de utilizador já existe."
            )

            return redirect(
                "adicionar_professor"
            )

        if User.objects.filter(
            telefone=telefone
        ).exists():

            messages.error(
                request,
                "Este telefone já está associado a outro utilizador."
            )

            return redirect(
                "adicionar_professor"
            )

        if email and User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Este e-mail já está associado a outro utilizador."
            )

            return redirect(
                "adicionar_professor"
            )

        # ==========================
        # CRIAR UTILIZADOR
        # ==========================

        user = User.objects.create_user(

            username=username,

            first_name=nome_completo,

            email=email,

            telefone=telefone,

            password=password,

            role="PROFESSOR",

            escola=escola,

        )

        # ==========================
        # CRIAR PROFESSOR
        # ==========================

        professor = Professor.objects.create(

            usuario=user,

            escola=escola,

            disciplina=disciplina,

            classes=classes,

        )

        professor.turmas.set(
            turmas_ids
        )

        messages.success(

            request,

            f"Professor '{nome_completo}' criado com sucesso."

        )

        return redirect(
            "professores"
        )

    return render(

        request,

        "adicionar_professor.html",

        {
            "turmas": turmas,
        },

    )


# ==========================================
    # ADICIONAR TURMAS
# ==========================================
@login_required
def adicionar_turma(request):

    if request.user.role != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    escola = request.user.escola

    cursos = Curso.objects.filter(
        escola=escola
    ).order_by("nome")

    # ==========================================
    # BUSCAR ANO LETIVO ATIVO
    # ==========================================

    ano_letivo_obj = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo_obj:

        messages.error(
            request,
            "Nenhum ano letivo ativo encontrado."
        )

        return redirect("dashboard")

    # ==========================================
    # POST
    # ==========================================

    if request.method == "POST":

        classe = request.POST.get("classe", "").strip()
        identificador = request.POST.get("identificador", "").strip()
        turno = request.POST.get("turno", "").strip()
        curso_id = request.POST.get("curso")

        if not all([classe, identificador, turno]):

            messages.error(
                request,
                "Preencha todos os campos obrigatórios."
            )

            return redirect("adicionar_turma")

        # ==========================================
        # CURSO
        # ==========================================

        curso_obj = None

        if curso_id:

            curso_obj = Curso.objects.filter(
                id=curso_id,
                escola=escola
            ).first()

        # ==========================================
        # VERIFICAR DUPLICIDADE
        # ==========================================

        existe = Turma.objects.filter(
            classe=classe,
            identificador=identificador,
            turno=turno,
            ano_letivo=ano_letivo_obj,
            escola=escola,
            curso=curso_obj
        ).exists()

        if existe:

            messages.error(
                request,
                "Já existe uma turma com estes dados."
            )

            return redirect("adicionar_turma")

        # ==========================================
        # CRIAR TURMA
        # ==========================================

        try:

            with transaction.atomic():

                Turma.objects.create(
                    classe=classe,
                    identificador=identificador,
                    turno=turno,
                    ano_letivo=ano_letivo_obj,
                    escola=escola,
                    curso=curso_obj
                )

                messages.success(
                    request,
                    f"Turma criada no ano letivo {ano_letivo_obj.nome}."
                )

                return redirect("turmas")

        except Exception as e:

            messages.error(
                request,
                f"Erro ao criar turma: {str(e)}"
            )

            return redirect("adicionar_turma")

    # ==========================================
    # CONTEXT
    # ==========================================

    return render(request, "adicionar_turma.html", {

        "cursos": cursos,
        "ano_ativo": ano_letivo_obj

    })



# =====================================================
# DISCIPLINAS
# =====================================================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def lista_disciplinas(request):

    escola = get_escola(request)

    if not escola:
        return redirect('dashboard')

    user = request.user

    # =====================================
    # BASE TEMPLATE DINÂMICO (SEGURO)
    # =====================================
    if user.role == "DIRETOR_PEDAGOGICO":
        base_template = "base_diretor_pedagogico.html"

    elif user.role == "DIRETOR":
        base_template = "base.html"

    elif user.role == "PROFESSOR":
        base_template = "base_professor.html"

    elif user.role == "SECRETARIA":
        base_template = "base_secretaria.html"

    else:
        base_template = "base.html"

    # =====================================
    # ANO LETIVO ATIVO
    # =====================================
    ano_ativo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # =====================================
    # FILTRO POR ANO (OPCIONAL)
    # =====================================
    ano_id = request.GET.get("ano")

    # =====================================
    # BASE QUERYSET
    # =====================================
    if user.role in ["DIRETOR", "DIRETOR_PEDAGOGICO"]:

        disciplinas = Disciplina.objects.filter(
            escola=escola
        )

    elif user.role == "PROFESSOR":

        disciplinas = Disciplina.objects.filter(
            escola=escola,
            professor=user
        )

    else:
        return redirect("dashboard")

    # =====================================
    # FILTRAR POR ANO LETIVO
    # =====================================
    if ano_id:

        disciplinas = disciplinas.filter(
            turma__ano_letivo_id=ano_id
        )

    else:

        disciplinas = disciplinas.filter(
            turma__ano_letivo=ano_ativo
        )

    # =====================================
    # ANOS PARA O FILTRO
    # =====================================
    anos = AnoLetivo.objects.filter(
        escola=escola
    ).order_by("-nome")

    # =====================================
    # CONTEXTO
    # =====================================
    return render(request, "disciplinas.html", {
        "disciplinas": disciplinas,
        "anos": anos,
        "ano_selecionado": ano_id,
        "ano_ativo": ano_ativo,
        "base_template": base_template,
    })


@login_required
def adicionar_disciplina(request):

    if request.user.role != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    escola = request.user.escola

    # ============================================
    # ANO LETIVO ATIVO
    # ============================================
    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        messages.error(
            request,
            "Nenhum ano letivo ativo encontrado."
        )
        return redirect("disciplinas")

    # ============================================
    # TURMAS APENAS DO ANO ATIVO
    # ============================================
    turmas = Turma.objects.filter(
        escola=escola,
        ano_letivo=ano_letivo
    ).select_related(
        "curso"
    ).order_by(
        "classe",
        "identificador"
    )

    # ============================================
    # PROFESSORES
    # ============================================
    professores = User.objects.filter(
        escola=escola,
        role="PROFESSOR"
    ).order_by(
        "username"
    )

    if request.method == "POST":

        nome = request.POST.get(
            "nome",
            ""
        ).strip()

        turma_id = request.POST.get("turma")
        professor_id = request.POST.get("professor")

        if not nome or not turma_id:

            messages.error(
                request,
                "Nome da disciplina e turma são obrigatórios."
            )

            return redirect(
                "adicionar_disciplina"
            )

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola,
            ano_letivo=ano_letivo
        )

        professor = None

        if professor_id:

            professor = User.objects.filter(
                id=professor_id,
                escola=escola,
                role="PROFESSOR"
            ).first()

        if Disciplina.objects.filter(
            nome__iexact=nome,
            turma=turma,
            escola=escola
        ).exists():

            messages.error(
                request,
                "Esta disciplina já existe nesta turma."
            )

            return redirect(
                "adicionar_disciplina"
            )

        Disciplina.objects.create(
            nome=nome,
            turma=turma,
            professor=professor,
            escola=escola
        )

        messages.success(
            request,
            "Disciplina criada com sucesso."
        )

        return redirect(
            "disciplinas"
        )

    return render(
        request,
        "adicionar_disciplina.html",
        {
            "turmas": turmas,
            "professores": professores,
            "ano_letivo": ano_letivo,
        }
    )


@login_required
def editar_disciplina(request, pk):

    if request.user.role != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    disciplina = get_object_or_404(
        Disciplina,
        pk=pk,
        escola=request.user.escola
    )

    professores = User.objects.filter(
        escola=request.user.escola,
        role="PROFESSOR"
    )

    if request.method == "POST":

        disciplina.nome = request.POST.get("nome")

        professor_id = request.POST.get("professor")

        if professor_id:
            disciplina.professor_id = professor_id
        else:
            disciplina.professor = None

        disciplina.save()

        messages.success(
            request,
            "Disciplina atualizada com sucesso."
        )

        return redirect("disciplinas")

    return render(
        request,
        "editar_disciplina.html",
        {
            "disciplina": disciplina,
            "professores": professores,
        }
    )




# =====================================================
# CALCULAR MÉDIA
# =====================================================

def calcular_media_anual(aluno, ano_letivo):

    notas = Nota.objects.filter(
        aluno=aluno,
        ano_letivo=ano_letivo
    )

    if not notas.exists():
        return 0

    medias = []

    for nota in notas:

        valores = []

        # P1
        if nota.p1 is not None:
            valores.append(float(nota.p1))

        # P2
        if nota.p2 is not None:
            valores.append(float(nota.p2))

        # MÉDIA
        if nota.media is not None:
            valores.append(float(nota.media))

        if valores:
            media_disciplina = sum(valores) / len(valores)
            medias.append(media_disciplina)

    if not medias:
        return 0

    media_final = sum(medias) / len(medias)

    return round(media_final, 2)





# =====================================================
# PAINEL DO DIRETOR
# =====================================================

@login_required
def painel_diretor(request):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    escola = request.user.escola
    ano_letivo = request.GET.get("ano", "2025-2026")

    total_alunos = Aluno.objects.filter(escola=escola).count()
    total_professores = User.objects.filter(
        escola=escola,
        role="PROFESSOR"
    ).count()

    total_turmas = Turma.objects.filter(escola=escola).count()

    trimestres = Trimestre.objects.filter(
        escola=escola,
        ano_letivo=ano_letivo
    ).order_by('ordem')

    aprovados = 0
    reprovados = 0

    alunos = Aluno.objects.filter(escola=escola)

    for aluno in alunos:
        media = calcular_media_anual(aluno, ano_letivo)

        if media >= 10:
            aprovados += 1
        else:
            reprovados += 1

    percent_aprovacao = (
        (aprovados / total_alunos) * 100
        if total_alunos > 0 else 0
    )

    return render(request, "dashboard.html", {
        "total_alunos": total_alunos,
        "total_professores": total_professores,
        "total_turmas": total_turmas,
        "aprovados": aprovados,
        "reprovados": reprovados,
        "percent_aprovacao": round(percent_aprovacao, 2),
        "ano_letivo": ano_letivo
    })

# ==========================================================
# DASHBOARD PROFESSOR
# ==========================================================

@login_required
def dashboard_professor(request):

    # ======================================================
    # PERMISSÃO
    # ======================================================

    if getattr(request.user, "role", None) != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    # ======================================================
    # ANO LETIVO ATIVO
    # ======================================================

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # ======================================================
    # ESCOLA
    # ======================================================

    escola_nome = (
        escola.nome
        if escola
        else "Sem escola vinculada"
    )

    # ======================================================
    # DISCIPLINAS DO PROFESSOR
    # ======================================================

    disciplinas_prof = Disciplina.objects.filter(
        professor=professor,
        escola=escola
    ).select_related(
        "turma",
        "turma__ano_letivo"
    )

    # ======================================================
    # TURMAS DO PROFESSOR
    # ======================================================

    turmas = (
        Turma.objects
        .filter(
            disciplinas__professor=professor,
            ano_letivo=ano_letivo
        )
        .select_related(
            "curso",
            "ano_letivo"
        )
        .distinct()
        .order_by(
            "classe",
            "identificador"
        )
    )

    total_turmas = turmas.count()

    total_alunos = Aluno.objects.filter(
        turma__in=turmas
    ).count()

    total_disciplinas = disciplinas_prof.count()

    # ======================================================
    # TURMA SELECIONADA
    # ======================================================

    turma_id = request.GET.get("turma")

    turma_selecionada = None

    disciplinas = []

    if turma_id:

        turma_selecionada = turmas.filter(
            id=turma_id
        ).first()

        # ==================================================
        # ALUNOS
        # ==================================================

        if turma_selecionada:

            alunos = (
                Aluno.objects
                .filter(
                    turma=turma_selecionada
                )
                .select_related("usuario")
                .order_by("numero_processo")
            )

            # ==============================================
            # DISCIPLINAS DA TURMA
            # ==============================================

            disciplinas_qs = disciplinas_prof.filter(
                turma=turma_selecionada
            )

            for disciplina in disciplinas_qs:

                alunos_disciplina = []

                for aluno in alunos:

                    # ======================================
                    # NOTAS DO ANO LETIVO
                    # ======================================

                    notas = Nota.objects.filter(
                        aluno=aluno,
                        disciplina=disciplina,
                        ano_letivo=ano_letivo
                    )

                    medias = []

                    for nota in notas:

                        if nota.media is not None:
                            medias.append(float(nota.media))

                    # ======================================
                    # MÉDIA FINAL
                    # ======================================

                    media_final = None

                    if medias:

                        media_final = round(
                            sum(medias) / len(medias),
                            1
                        )

                    # ======================================
                    # STATUS
                    # ======================================

                    status = None

                    if media_final is not None:

                        status = (
                            "aprovado"
                            if media_final >= 10
                            else "reprovado"
                        )

                    alunos_disciplina.append({

                        "id": aluno.id,

                        "nome": (
                            aluno.usuario.get_full_name()
                            or aluno.usuario.username
                        ),

                        "numero_processo": aluno.numero_processo,

                        "media_final": media_final,

                        "status": status,

                    })

                disciplinas.append({

                    "nome": disciplina.nome,

                    "alunos": alunos_disciplina

                })

    # ======================================================
    # CONTEXT
    # ======================================================

    context = {

        "escola_nome": escola_nome,

        "ano_letivo": ano_letivo,

        "total_turmas": total_turmas,

        "total_alunos": total_alunos,

        "total_disciplinas": total_disciplinas,

        "turmas": turmas,

        "turma_selecionada": turma_selecionada,

        "disciplinas": disciplinas,

    }

    return render(
        request,
        "dashboard_professor.html",
        context
    )



# =====================================================
    # HISTÓRICO DE NOTAS
# =====================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def historico_notas(request):

    professor = request.user
    escola = professor.escola

    # =====================================================
    # FILTROS
    # =====================================================
    ano_id = request.GET.get("ano_letivo")
    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    trimestre = request.GET.get("trimestre")

    # =====================================================
    # ANOS LETIVOS
    # =====================================================
    anos_letivos = (
        AnoLetivo.objects
        .filter(escola=escola)
        .order_by("-id")
    )

    # =====================================================
    # TURMAS
    # =====================================================
    turmas = (
        Turma.objects
        .filter(
            escola=escola,
            disciplinas__professor=professor
        )
        .distinct()
        .select_related("curso", "ano_letivo")
    )

    if ano_id:
        turmas = turmas.filter(
            ano_letivo_id=ano_id
        )

    turmas = turmas.order_by(
        "classe",
        "identificador"
    )

    # =====================================================
    # DISCIPLINAS
    # =====================================================
    disciplinas = (
        Disciplina.objects
        .filter(
            escola=escola,
            professor=professor
        )
        .select_related(
            "turma",
            "turma__curso",
            "turma__ano_letivo"
        )
    )

    # MOSTRAR APENAS DISCIPLINAS DO ANO SELECIONADO
    if ano_id:
        disciplinas = disciplinas.filter(
            turma__ano_letivo_id=ano_id
        )

    # SE ESCOLHER TURMA
    if turma_id:
        disciplinas = disciplinas.filter(
            turma_id=turma_id
        )

    disciplinas = disciplinas.order_by("nome")

    # =====================================================
    # NOTAS
    # =====================================================
    notas_qs = Nota.objects.filter(
        escola=escola,
        disciplina__professor=professor
    )

    if ano_id:
        notas_qs = notas_qs.filter(
            ano_letivo_id=ano_id
        )

    if turma_id:
        notas_qs = notas_qs.filter(
            aluno__turma_id=turma_id
        )

    if disciplina_id:
        notas_qs = notas_qs.filter(
            disciplina_id=disciplina_id
        )

    if trimestre:
        try:
            notas_qs = notas_qs.filter(
                trimestre=int(trimestre)
            )
        except (ValueError, TypeError):
            notas_qs = notas_qs.none()

    # =====================================================
    # PERFORMANCE
    # =====================================================
    notas_qs = (
        notas_qs
        .select_related(
            "aluno",
            "aluno__usuario",
            "aluno__turma",
            "aluno__turma__curso",
            "disciplina",
            "ano_letivo"
        )
        .order_by("-id")
    )

    # =====================================================
    # CONTEXT
    # =====================================================
    context = {
        "notas": notas_qs,
        "anos_letivos": anos_letivos,
        "turmas": turmas,
        "disciplinas": disciplinas,

        "ano_id": ano_id,
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
        "trimestre": trimestre,
    }

    return render(
        request,
        "historico_notas.html",
        context
    )


# ==========================================================
# MINHAS TURMAS
# ==========================================================

@login_required
def minhas_turmas(request):


    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        return render(
            request,
            "minhas_turmas.html",
            {
                "turmas": [],
                "total_turmas": 0,
                "ano_letivo": None,
            }
        )

    turmas = (
        Turma.objects
        .filter(
            escola=escola,
            ano_letivo=ano_letivo,
            disciplinas__professor=professor
        )
        .distinct()
        .order_by(
            "classe",
            "identificador"
        )
    )

    context = {
        "turmas": turmas,
        "total_turmas": turmas.count(),
        "ano_letivo": ano_letivo,
    }

    return render(
        request,
        "minhas_turmas.html",
        context
    )



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

@login_required
def alunos_da_turma(request, turma_id):

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola,
    )

    alunos = (
        Aluno.objects.filter(
            turma=turma,
            escola=request.user.escola,
            ativo=True,
        )
        .select_related(
            "usuario",
            "curso",
        )
        .order_by("numero_na_turma")
    )

    # Todas as disciplinas deste professor nesta turma
    disciplinas = (
        Disciplina.objects.filter(
            turma=turma,
            professor=request.user,
            escola=request.user.escola,
        )
        .order_by("nome")
    )

    context = {
        "turma": turma,
        "alunos": alunos,
        "disciplinas": disciplinas,
        "total_alunos": alunos.count(),
        "total_masculinos": alunos.filter(
            sexo="Masculino"
        ).count(),
        "total_femininos": alunos.filter(
            sexo="Feminino"
        ).count(),
        "total_aprovados": alunos.filter(
            aprovado=True
        ).count(),
        "total_reprovados": alunos.filter(
            aprovado=False
        ).count(),
    }

    return render(
        request,
        "alunos_da_turma.html",
        context,
    )


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

@login_required
def marcar_frequencia(request, turma_id, disciplina_id):

    # =====================================================
    # PERMISSÃO
    # =====================================================

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    # =====================================================
    # TURMA
    # =====================================================

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=escola,
    )

    # =====================================================
    # DISCIPLINA
    # =====================================================

    disciplina = get_object_or_404(
        Disciplina,
        id=disciplina_id,
        turma=turma,
        professor=professor,
        escola=escola,
    )

    # =====================================================
    # DATA
    # =====================================================

    hoje = timezone.localdate()

    if hoje.weekday() in [5, 6]:
        messages.warning(
            request,
            "Não é permitido lançar frequências aos sábados e domingos."
        )

        return redirect(
            "alunos_da_turma",
            turma_id=turma.id,
        )

    # =====================================================
    # ALUNOS
    # =====================================================

    alunos = (
        Aluno.objects
        .filter(
            turma=turma,
            escola=escola,
            ativo=True,
        )
        .order_by("numero_na_turma")
    )

    # =====================================================
    # GUARDAR
    # =====================================================

    if request.method == "POST":

        for aluno in alunos:

            presente = (
                request.POST.get(
                    f"presente_{aluno.id}"
                ) == "on"
            )

            # Só faz sentido justificar quando existe falta
            if presente:
                justificada = False
            else:
                justificada = (
                    request.POST.get(
                        f"justificada_{aluno.id}"
                    ) == "on"
                )

            observacao = (
                request.POST.get(
                    f"observacao_{aluno.id}",
                    ""
                ).strip()
            )

            Frequencia.objects.update_or_create(

                aluno=aluno,
                disciplina=disciplina,
                data=hoje,

                defaults={

                    "presente": presente,
                    "justificada": justificada,
                    "observacao": observacao,
                    "professor": professor,
                    "escola": escola,

                },

            )

        messages.success(
            request,
            "Frequências registadas com sucesso."
        )

        return redirect(
            "marcar_frequencia",
            turma_id=turma.id,
            disciplina_id=disciplina.id,
        )

    # =====================================================
    # FREQUÊNCIAS EXISTENTES
    # =====================================================

    frequencias = {
        f.aluno_id: f
        for f in Frequencia.objects.filter(
            disciplina=disciplina,
            data=hoje,
        )
    }

    # =====================================================
    # CONTEXTO
    # =====================================================

    context = {

        "turma": turma,
        "disciplina": disciplina,
        "alunos": alunos,
        "hoje": hoje,
        "frequencias": frequencias,

    }

    return render(
        request,
        "marcar_frequencia.html",
        context,
    )


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.utils import timezone

@login_required
def painel_diretor_frequencia(request):

    if request.user.role != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    escola = request.user.escola

    # ==========================
    # FILTROS
    # ==========================

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    aluno_id = request.GET.get("aluno")
    mes = request.GET.get("mes")

    frequencias = (
        Frequencia.objects
        .filter(escola=escola)
        .select_related(
            "aluno",
            "aluno__usuario",
            "disciplina",
            "aluno__turma"
        )
    )

    if turma_id:
        frequencias = frequencias.filter(aluno__turma_id=turma_id)

    if disciplina_id:
        frequencias = frequencias.filter(disciplina_id=disciplina_id)

    if aluno_id:
        frequencias = frequencias.filter(aluno_id=aluno_id)

    if mes:
        try:
            frequencias = frequencias.filter(data__month=int(mes))
        except (ValueError, TypeError):
            pass

    # ==========================
    # KPIs
    # ==========================

    total_faltas = frequencias.filter(presente=False).count()
    total_presencas = frequencias.filter(presente=True).count()
    total_registos = frequencias.count()

    taxa_presenca = (
        round((total_presencas / total_registos) * 100, 1)
        if total_registos > 0 else 0
    )

    # ==========================
    # TOP ALUNOS COM MAIS FALTAS
    # ==========================

    top_faltas_alunos = (
        frequencias
        .filter(presente=False)
        .values(
            "aluno__id",
            "aluno__usuario__first_name",
            "aluno__usuario__last_name",
        )
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # ==========================
    # FREQUÊNCIA POR TURMA (CLASSE + IDENTIFICADOR)
    # ==========================

    frequencia_por_turma = (
        frequencias
        .values(
            "aluno__turma__id",
            "aluno__turma__classe",
            "aluno__turma__identificador"
        )
        .annotate(
            presencas=Count("id", filter=Q(presente=True)),
            faltas=Count("id", filter=Q(presente=False))
        )
        .order_by("aluno__turma__classe", "aluno__turma__identificador")
    )

    # ==========================
    # CONTEXTO
    # ==========================

    context = {

        "frequencias": frequencias,

        "total_faltas": total_faltas,
        "total_presencas": total_presencas,
        "taxa_presenca": taxa_presenca,

        "top_faltas_alunos": top_faltas_alunos,
        "frequencia_por_turma": frequencia_por_turma,

        "turmas": Turma.objects.filter(escola=escola),
        "disciplinas": Disciplina.objects.filter(escola=escola),
        "alunos": Aluno.objects.filter(escola=escola).select_related("usuario"),

        "filtros": {
            "turma": turma_id,
            "disciplina": disciplina_id,
            "aluno": aluno_id,
            "mes": mes,
        }

    }

    return render(
        request,
        "painel_diretor_frequencia.html",
        context
    )



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

@login_required
def relatorios_professor(request):

    if getattr(request.user, "role", None) != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    disciplinas = Disciplina.objects.filter(
        professor=professor,
        escola=escola,
        turma__ano_letivo=ano_letivo
    ).select_related("turma")

    turmas = Turma.objects.filter(
        disciplinas__in=disciplinas,
        ano_letivo=ano_letivo
    ).distinct()

    dados = []

    total_alunos_geral = 0
    total_aprovados_geral = 0
    medias = []

    for turma in turmas:

        alunos = turma.alunos.all()

        media = alunos.aggregate(
            media=Avg("media_final")
        )["media"] or 0

        total = alunos.count()
        aprovados = alunos.filter(aprovado=True).count()

        percentagem = (aprovados / total) * 100 if total > 0 else 0

        total_alunos_geral += total
        total_aprovados_geral += aprovados
        medias.append(float(media))

        dados.append({
            "turma": turma,
            "media": round(float(media), 2),
            "percentagem": round(percentagem, 1),
            "total_alunos": total,
            "total_aprovados": aprovados
        })

    media_global = round(sum(medias) / len(medias), 2) if medias else 0
    percent_global = round((total_aprovados_geral / total_alunos_geral) * 100, 1) if total_alunos_geral else 0

    # =========================
    # PDF EXPORT
    # =========================
    if request.GET.get("export") == "pdf":

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="relatorios_professor.pdf"'

        doc = SimpleDocTemplate(response)
        styles = getSampleStyleSheet()

        elements = []

        elements.append(Paragraph("Relatório do Professor", styles["Title"]))
        elements.append(Spacer(1, 12))

        data = [["Turma", "Alunos", "Média", "Aprovados", "%"]]

        for item in dados:
            data.append([
                str(item["turma"]),
                item["total_alunos"],
                item["media"],
                item["total_aprovados"],
                f'{item["percentagem"]}%'
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))

        elements.append(table)

        doc.build(elements)

        return response

    context = {
        "dados": dados,
        "ano_letivo": ano_letivo,
        "media_global": media_global,
        "percent_global": percent_global,
        "total_turmas": len(dados),
        "total_alunos_geral": total_alunos_geral,
    }

    return render(request, "relatorios.html", context)


# ==========================================================
# LANÇAR NOTAS
# ==========================================================

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from academic.models import (
    FechamentoNota,
    FechamentoTrimestre,
    Nota,
    Disciplina,
    AnoLetivo
)


@login_required
def lancar_notas(request):

    # =====================================================
    # PERMISSÃO
    # =====================================================
    if getattr(request.user, "role", None) != "PROFESSOR":
        return redirect("dashboard_professor")

    professor = request.user
    escola = professor.escola

    # =====================================================
    # ANO LETIVO
    # =====================================================
    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        messages.error(request, "Nenhum ano letivo ativo encontrado.")
        return redirect("dashboard_professor")

    # =====================================================
    # HELPERS
    # =====================================================
    def parse_trimestre(value):
        try:
            return int(value)
        except:
            return None

    def escala_maxima(disciplina):
        try:
            classe = int(disciplina.turma.classe)
        except:
            return 20
        return 10 if classe <= 6 else 20

    def limitar_nota(valor, max_nota):
        if valor in [None, ""]:
            return None
        try:
            return min(float(valor), max_nota)
        except:
            return None

    def etapa_fechada(disciplina, trimestre, etapa):
        if not disciplina or not trimestre:
            return False

        return FechamentoNota.objects.filter(
            disciplina=disciplina,
            trimestre=trimestre,
            ano_letivo=ano_letivo,
            etapa=etapa,
            fechado=True
        ).exists()

    # =====================================================
    # GET PARAMS
    # =====================================================
    disciplina_id = request.GET.get("disciplina")
    trimestre = parse_trimestre(request.GET.get("trimestre"))

    disciplinas = Disciplina.objects.filter(
        professor=professor,
        escola=escola,
        turma__ano_letivo=ano_letivo
    ).select_related("turma").order_by("nome")

    disciplina = None
    alunos = None
    notas_existentes = {}

    fechamento = None
    trimestre_fechado = False

    mostrar_exame = False
    mostrar_recurso = False
    alunos_com_recurso = []

    # =====================================================
    # CARREGAMENTO GET
    # =====================================================
    if disciplina_id:

        disciplina = get_object_or_404(
            Disciplina,
            id=disciplina_id,
            professor=professor,
            escola=escola
        )

        alunos = disciplina.turma.alunos.select_related("usuario").all()

        notas = Nota.objects.filter(
            disciplina=disciplina,
            trimestre=trimestre,
            ano_letivo=ano_letivo
        )

        notas_existentes = {n.aluno.id: n for n in notas}

        try:
            classe = int(disciplina.turma.classe)
            mostrar_exame = (classe in [6, 9, 12] and trimestre == 3)
        except:
            mostrar_exame = False

        if trimestre == 3:
            mostrar_recurso = True
            alunos_com_recurso = [
                n.aluno.id for n in notas
                if n.media_final is not None and n.media_final < 10
            ]

        fechamento = FechamentoTrimestre.objects.filter(
            disciplina=disciplina,
            trimestre=trimestre,
            ano_letivo=ano_letivo
        ).first()

        if fechamento and fechamento.fechado:
            trimestre_fechado = True

    # =====================================================
    # POST
    # =====================================================
    if request.method == "POST":

        acao = request.POST.get("acao")
        disciplina_id = request.POST.get("disciplina")
        trimestre = parse_trimestre(request.POST.get("trimestre"))

        if not disciplina_id or not trimestre:
            messages.error(request, "Dados inválidos.")
            return redirect("lancar_notas")

        disciplina = get_object_or_404(
            Disciplina,
            id=disciplina_id,
            professor=professor,
            escola=escola
        )

        fechamento, _ = FechamentoTrimestre.objects.get_or_create(
            disciplina=disciplina,
            trimestre=trimestre,
            ano_letivo=ano_letivo
        )

        max_nota = escala_maxima(disciplina)

        # =================================================
        # SALVAR NOTAS
        # =================================================
        if acao == "salvar":

            if fechamento.fechado:
                messages.error(request, "Trimestre fechado.")
                return redirect(request.get_full_path())

            alunos = disciplina.turma.alunos.all()

            for aluno in alunos:

                nota_obj, _ = Nota.objects.get_or_create(
                    aluno=aluno,
                    disciplina=disciplina,
                    trimestre=trimestre,
                    ano_letivo=ano_letivo,
                    defaults={"escola": escola}
                )

                # P1
                p1 = request.POST.get(f"p1_{aluno.id}")
                if p1 not in [None, ""] and not etapa_fechada(disciplina, trimestre, "P1"):
                    nota_obj.p1 = Decimal(limitar_nota(p1, max_nota))

                # P2
                p2 = request.POST.get(f"p2_{aluno.id}")
                if p2 not in [None, ""] and not etapa_fechada(disciplina, trimestre, "P2"):
                    nota_obj.p2 = Decimal(limitar_nota(p2, max_nota))

                # EXAME
                if mostrar_exame:
                    exame = request.POST.get(f"exame_{aluno.id}")
                    if exame not in [None, ""] and not etapa_fechada(disciplina, trimestre, "EXAME"):
                        nota_obj.exame = Decimal(limitar_nota(exame, max_nota))
                else:
                    nota_obj.exame = None

                # RECURSO
                if mostrar_recurso:
                    rec = request.POST.get(f"recurso_{aluno.id}")
                    if rec not in [None, ""] and not etapa_fechada(disciplina, trimestre, "RECURSO"):
                        nota_obj.recurso = Decimal(limitar_nota(rec, max_nota))

                nota_obj.save()

            messages.success(request, "Notas lançadas com sucesso.")
            return redirect(request.get_full_path())

        # =================================================
        # FECHAR P1 / P2 / EXAME / RECURSO / TRIMESTRE
        # =================================================
        elif acao in ["fechar_p1", "fechar_p2", "fechar_exame", "fechar_recurso"]:

            etapa_map = {
                "fechar_p1": "P1",
                "fechar_p2": "P2",
                "fechar_exame": "EXAME",
                "fechar_recurso": "RECURSO",
            }

            FechamentoNota.objects.update_or_create(
                disciplina=disciplina,
                trimestre=trimestre,
                ano_letivo=ano_letivo,
                etapa=etapa_map[acao],
                defaults={
                    "fechado": True,
                    "fechado_por": request.user,
                    "data_fechamento": timezone.now()
                }
            )

            messages.success(request, f"{etapa_map[acao]} fechado.")
            return redirect(request.get_full_path())

        elif acao == "fechar":

            if fechamento.fechado:
                messages.warning(request, "Já está fechado.")
            else:
                fechamento.fechado = True
                fechamento.fechado_por = request.user
                fechamento.data_fechamento = timezone.now()
                fechamento.save()

                messages.success(request, "Trimestre fechado.")

            return redirect(request.get_full_path())

    # =====================================================
    # CONTEXT
    # =====================================================
    context = {
        "ano_letivo": ano_letivo,
        "disciplinas": disciplinas,
        "disciplina": disciplina,
        "alunos": alunos,
        "notas_existentes": notas_existentes,

        "p1_fechado": etapa_fechada(disciplina, trimestre, "P1") if disciplina else False,
        "p2_fechado": etapa_fechada(disciplina, trimestre, "P2") if disciplina else False,
        "exame_fechado": etapa_fechada(disciplina, trimestre, "EXAME") if disciplina else False,
        "recurso_fechado": etapa_fechada(disciplina, trimestre, "RECURSO") if disciplina else False,

        "trimestre": trimestre,
        "trimestre_fechado": trimestre_fechado,
        "fechamento": fechamento,

        "mostrar_exame": mostrar_exame,
        "mostrar_recurso": mostrar_recurso,
        "alunos_com_recurso": alunos_com_recurso,
    }

    return render(request, "lancar_notas.html", context)


#=================================================================
#      DASHBOARD ALUNO
#=================================================================

from decimal import Decimal

from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import *


@login_required
def dashboard_aluno(request):

    # =========================================================
    # VERIFICAÇÃO DE PERMISSÃO
    # =========================================================

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    # =========================================================
    # BUSCAR ALUNO
    # =========================================================

    aluno = (
        Aluno.objects
        .select_related(
            "turma",
            "turma__ano_letivo",
            "turma__escola"
        )
        .filter(usuario=request.user)
        .first()
    )

    if not aluno:
        return redirect("dashboard")

    # =========================================================
    # ANO LETIVO ATUAL
    # =========================================================

    ano_letivo = aluno.turma.ano_letivo

    # =========================================================
    # BUSCAR NOTAS APENAS DO ANO ATUAL
    # =========================================================

    notas = (
        Nota.objects
        .filter(
            aluno=aluno,
            ano_letivo=ano_letivo
        )
        .select_related("disciplina")
        .order_by("disciplina__nome", "trimestre")
    )

    # =========================================================
    # AGRUPAR DISCIPLINAS
    # =========================================================

    disciplinas = {}

    for nota in notas:

        disc = nota.disciplina.nome

        if disc not in disciplinas:

            disciplinas[disc] = {

                1: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                2: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                3: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                "media_final": 0

            }

        # =====================================================
        # EVITAR ERRO DECIMAL + FLOAT
        # =====================================================

        p1 = nota.p1 if nota.p1 is not None else Decimal("0")
        p2 = nota.p2 if nota.p2 is not None else Decimal("0")

        media_trimestre = (p1 + p2) / Decimal("2")

        disciplinas[disc][nota.trimestre] = {

            "p1": nota.p1,
            "p2": nota.p2,
            "media": round(float(media_trimestre), 1)

        }

    # =========================================================
    # CALCULAR MÉDIA FINAL POR DISCIPLINA
    # =========================================================

    soma_medias = 0
    qtd_disciplinas = len(disciplinas)

    for disc, dados in disciplinas.items():

        medias = []

        for t in [1, 2, 3]:

            media = dados[t]["media"]

            if media is not None:
                medias.append(float(media))

        media_final_disc = (

            round(sum(medias) / len(medias), 1)

            if medias else 0

        )

        dados["media_final"] = media_final_disc

        soma_medias += media_final_disc

    # =========================================================
    # MÉDIA FINAL DO ANO
    # =========================================================

    media_final_ano = (

        round(soma_medias / qtd_disciplinas, 1)

        if qtd_disciplinas else 0

    )

    aprovado = media_final_ano >= 10

    # =========================================================
    # SECRETARIA / DÍVIDAS
    # =========================================================

    dividas = Mensalidade.objects.filter(

        aluno=aluno,
        status__in=["PENDENTE", "ATRASADA"]

    )

    tem_divida = dividas.exists()

    total_divida = (

        dividas.aggregate(total=Sum("valor"))["total"]

        or Decimal("0")

    )

    # =========================================================
    # HORÁRIO
    # =========================================================

    horario = Horario.objects.filter(
        turma=aluno.turma
    ).first()

    aulas = None

    if horario:

        aulas = (
            Aula.objects
            .filter(horario=horario)
            .select_related("disciplina")
            .order_by("dia", "hora_inicio")
        )

    # =========================================================
    # HISTÓRICO ACADÉMICO
    # =========================================================

    historicos = (
        HistoricoAcademico.objects
        .filter(aluno=aluno)
        .select_related("ano_letivo", "turma")
        .order_by("-criado_em")
    )

    from django.utils import timezone



    # =========================================================
    # RESUMO DO MÊS ATUAL
    # =========================================================



    # =========================================================
    # CONTEXTO
    # =========================================================

    context = {

        "aluno": aluno,
        "disciplinas": disciplinas,
        "media_final_ano": media_final_ano,
        "aprovado": aprovado,
        "tem_divida": tem_divida,
        "total_divida": total_divida,
        "horario": horario,
        "aulas": aulas,
        "historicos": historicos,


    }

    return render(
        request,
        "dashboard_aluno.html",
        context
    )


# ==========================================================
# FREQUÊNCIAS DO ALUNO
# ==========================================================
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, redirect

@login_required
def frequencia_aluno(request):

    # ==========================================================
    # PERMISSÃO
    # ==========================================================

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    # ==========================================================
    # ALUNO
    # ==========================================================

    aluno = (
        Aluno.objects
        .select_related("turma")
        .filter(usuario=request.user)
        .first()
    )

    if not aluno:
        return redirect("dashboard")

    # ==========================================================
    # FILTRO POR MÊS
    # ==========================================================

    mes = request.GET.get("mes")

    frequencias = (
        Frequencia.objects
        .filter(aluno=aluno)
        .select_related("disciplina")
    )

    if mes:
        try:
            frequencias = frequencias.filter(
                data__month=int(mes)
            )
        except (ValueError, TypeError):
            mes = None

    frequencias = frequencias.order_by(
        "-data",
        "disciplina__nome"
    )

    # ==========================================================
    # KPIs
    # ==========================================================

    total_presencas = frequencias.filter(
        presente=True
    ).count()

    total_faltas = frequencias.filter(
        presente=False
    ).count()

    total_justificadas = frequencias.filter(
        presente=False,
        justificada=True
    ).count()

    total_registos = frequencias.count()

    percentagem_presencas = 0

    if total_registos > 0:
        percentagem_presencas = round(
            (total_presencas / total_registos) * 100,
            1
        )

    # ==========================================================
    # FALTAS POR DISCIPLINA
    # ==========================================================

    faltas_por_disciplina = (
        frequencias
        .filter(presente=False)
        .values("disciplina__nome")
        .annotate(
            total_faltas=Count("id")
        )
        .order_by(
            "-total_faltas",
            "disciplina__nome"
        )
    )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {
        "aluno": aluno,
        "frequencias": frequencias,
        "mes_selecionado": mes,
        "total_presencas": total_presencas,
        "total_faltas": total_faltas,
        "total_justificadas": total_justificadas,
        "total_registos": total_registos,
        "percentagem_presencas": percentagem_presencas,
        "faltas_por_disciplina": faltas_por_disciplina,
    }

    return render(
        request,
        "frequencias_aluno.html",
        context,
    )


# ============================================================
#                     BOLETIM INSTITUCIONAL
# ============================================================

import uuid
import os
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from django.db.models import Sum

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors

import qrcode




@login_required
def gerar_boletim_pdf(request):

    # =====================================
    # PERMISSÃO
    # =====================================

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    # =====================================
    # ALUNO
    # =====================================

    aluno = Aluno.objects.select_related(
        "usuario",
        "turma",
        "turma__escola",
        "turma__ano_letivo",
        "turma__curso"
    ).filter(
        usuario=request.user
    ).first()

    if not aluno:
        return redirect("dashboard")

    # =====================================
    # BLOQUEIO FINANCEIRO
    # =====================================

    dividas = Mensalidade.objects.filter(
        aluno=aluno,
        status__in=["ATRASADA"]
    )

    if dividas.exists():

        messages.error(
            request,
            "Regularize a mensalidade para gerar o boletim."
        )

        return redirect("dashboard_aluno")

    # =====================================
    # ANO LETIVO
    # =====================================

    ano_id = request.GET.get("ano")

    if ano_id:

        ano_letivo = AnoLetivo.objects.filter(
            id=ano_id,
            escola=aluno.escola
        ).first()

    else:

        ano_letivo = aluno.turma.ano_letivo

    if not ano_letivo:

        messages.error(
            request,
            "Ano letivo não encontrado."
        )

        return redirect("dashboard_aluno")

    # =====================================
    # HISTÓRICO ACADÉMICO
    # =====================================

    historico = HistoricoAcademico.objects.filter(
        aluno=aluno,
        ano_letivo=ano_letivo
    ).first()

    # =====================================
    # DEFINIR TURMA E CLASSE CORRETAS
    # =====================================

    if historico:

        turma_nome = (
            f"{historico.turma.classe}ª "
            f"{historico.turma.identificador}"
        )

        classe_nome = historico.classe

    else:

        turma_nome = (
            f"{aluno.turma.classe}ª "
            f"{aluno.turma.identificador}"
        )

        classe_nome = aluno.turma.classe

    # =====================================
    # DADOS ESCOLA
    # =====================================

    escola = aluno.escola

    numero_validacao = str(uuid.uuid4())[:12].upper()

    nome_aluno = (
        aluno.usuario.get_full_name()
        or aluno.usuario.username
    )

    numero_processo = aluno.numero_processo

    # =====================================
    # PDF
    # =====================================

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="boletim_{ano_letivo.nome}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    elementos = []

    # =====================================
    # CABEÇALHO OFICIAL ANGOLA
    # =====================================

    from reportlab.lib.enums import TA_CENTER

    estilo_centro = ParagraphStyle(
        "Centro",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        leading=16,
    )

    estilo_escola = ParagraphStyle(
        "Escola",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
    )

    # =====================================
    # INSÍGNIA DE ANGOLA
    # =====================================

    insignia_path = os.path.join(
        settings.MEDIA_ROOT,
        "insignia_angola.png"
    )

    if os.path.exists(insignia_path):
        insignia = Image(
            insignia_path,
            width=65,
            height=65
        )

        insignia.hAlign = "CENTER"

        elementos.append(insignia)

    # =====================================
    # TEXTO OFICIAL
    # =====================================

    elementos.append(
        Paragraph(
            "REPÚBLICA DE ANGOLA",
            estilo_centro
        )
    )

    elementos.append(
        Paragraph(
            "MINISTÉRIO DA EDUCAÇÃO",
            estilo_centro
        )
    )

    # =====================================
    # GOVERNO PROVINCIAL
    # =====================================

    if escola.provincia:
        elementos.append(
            Paragraph(
                f"GOVERNO PROVINCIAL DE {escola.provincia.upper()}",
                estilo_centro
            )
        )

    # =====================================
    # DIREÇÃO MUNICIPAL
    # =====================================

    if escola.municipio:
        elementos.append(
            Paragraph(
                f"DIREÇÃO MUNICIPAL DA EDUCAÇÃO DE {escola.municipio.upper()}",
                estilo_centro
            )
        )

    # =====================================
    # ENDEREÇO DA ESCOLA
    # =====================================

    if escola.endereco:
        elementos.append(
            Paragraph(
                escola.endereco.upper(),
                estilo_centro
            )
        )

    elementos.append(
        Paragraph(
            f"<b>{escola.nome.upper()}</b>",
            estilo_escola
        )
    )

    elementos.append(
        Spacer(1, 10))

    elementos.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.black
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    elementos.append(
        Paragraph(
            "<b>BOLETIM DE NOTAS</b>",
            ParagraphStyle(
                "TituloBoletim",
                parent=styles["Heading2"],
                alignment=TA_CENTER
            )
        )
    )

    elementos.append(
        Paragraph(
            f"Ano Letivo: <b>{ano_letivo.nome}</b>",
            ParagraphStyle(
                "AnoLetivo",
                parent=styles["Normal"],
                alignment=TA_CENTER
            )
        )
    )

    elementos.append(
        Spacer(1, 20)
    )

    # =====================================
    # DADOS ALUNO
    # =====================================

    dados_aluno = [

        ["Aluno", nome_aluno],

        ["Nº Processo", numero_processo],

        ["Classe", f"{classe_nome}ª Classe"],

        ["Turma", turma_nome],

        ["Ano Letivo", ano_letivo.nome],

        ["Código Validação", numero_validacao],

    ]

    tabela_dados = Table(
        dados_aluno,
        colWidths=[180, 300]
    )

    tabela_dados.setStyle(TableStyle([

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),

        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),

        ("FONTSIZE", (0, 0), (-1, -1), 10),

    ]))

    elementos.append(tabela_dados)

    elementos.append(
        Spacer(1, 25)
    )

    # =====================================
    # NOTAS DO ANO LETIVO
    # =====================================

    medias_finais = []

    for trimestre in [1, 2, 3]:

        notas = Nota.objects.filter(
            aluno=aluno,
            trimestre=trimestre,
            ano_letivo=ano_letivo
        ).select_related("disciplina").order_by(
            "disciplina__nome"
        )

        if not notas.exists():
            continue

        elementos.append(
            Paragraph(
                f"<b>{trimestre}º TRIMESTRE</b>",
                styles["Heading3"]
            )
        )

        elementos.append(
            Spacer(1, 10)
        )

        dados_tabela = [[
            "Disciplina",
            "P1",
            "P2",
            "Média",
            "Situação"
        ]]

        soma = 0
        contador = 0

        for nota in notas:

            media = nota.media or 0

            situacao = (
                "Aprovado"
                if media >= 10
                else "Reprovado"
            )

            soma += float(media)
            contador += 1

            dados_tabela.append([

                nota.disciplina.nome,

                nota.p1 if nota.p1 is not None else "-",

                nota.p2 if nota.p2 is not None else "-",

                media,

                situacao

            ])

        media_trimestre = (
            round(soma / contador, 2)
            if contador else 0
        )

        medias_finais.append(media_trimestre)

        tabela_notas = Table(
            dados_tabela,
            colWidths=[220, 60, 60, 60, 100]
        )

        tabela_notas.setStyle(TableStyle([

            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),

            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            ("ALIGN", (1, 1), (-1, -1), "CENTER"),

            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),

            ("FONTSIZE", (0, 0), (-1, -1), 9),

        ]))

        elementos.append(tabela_notas)

        elementos.append(
            Spacer(1, 15)
        )

        elementos.append(
            Paragraph(
                f"Média do Trimestre: <b>{media_trimestre}</b>",
                styles["Normal"]
            )
        )

        elementos.append(
            Spacer(1, 25)
        )

    # =====================================
    # MÉDIA FINAL
    # =====================================

    media_final = (
        round(sum(medias_finais) / len(medias_finais), 2)
        if medias_finais else 0
    )

    situacao_final = (
        "APROVADO"
        if media_final >= 10
        else "REPROVADO"
    )

    elementos.append(
        Spacer(1, 10)
    )

    resultado = Table([

        ["Média Final", media_final],

        ["Situação", situacao_final],

    ], colWidths=[220, 220])

    resultado.setStyle(TableStyle([

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),

        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, -1), 11),

    ]))

    elementos.append(resultado)

    elementos.append(
        Spacer(1, 30)
    )

    # =====================================
    # OBSERVAÇÃO HISTÓRICO
    # =====================================

    if historico:

        elementos.append(
            Paragraph(
                f"""
                <b>Observação:</b>
                Este boletim refere-se ao ano letivo
                {ano_letivo.nome},
                onde o aluno teve situação:
                <b>{historico.situacao}</b>.
                """,
                styles["Normal"]
            )
        )

    # =====================================
    # SALVAR BOLETIM
    # =====================================

    Boletim.objects.create(
        aluno=aluno,
        codigo_validacao=numero_validacao,
        media_anual=media_final,
        status_final=situacao_final
    )

    # =====================================
    # GERAR PDF
    # =====================================

    doc.build(elementos)

    return response



# ==========================================
# HORÁRIO DO ALUNO
# ==========================================

@login_required
def horario_aluno(request):
    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    aluno = Aluno.objects.select_related("turma", "turma__curso").filter(
        usuario=request.user
    ).first()

    if not aluno:
        return redirect("dashboard")

    horario = HorarioTurma.objects.filter(
        turma=aluno.turma
    ).first()

    dias = ["SEG", "TER", "QUA", "QUI", "SEX"]
    linhas = []

    # verificar se deve mostrar curso
    mostrar_curso = False
    try:
        if int(aluno.turma.classe) >= 10:
            mostrar_curso = True
    except:
        pass

    if horario:
        aulas = AulaHorario.objects.select_related("disciplina").filter(
            horario=horario
        ).order_by("hora_inicio")

        horas = sorted(list(set([a.hora_inicio for a in aulas])))

        for hora in horas:
            linha = {d: None for d in dias}
            linha["hora"] = hora

            for aula in aulas:
                if aula.hora_inicio == hora and aula.dia in dias:
                    linha[aula.dia] = aula

            linhas.append(linha)

    return render(request, "horario.html", {
        "aluno": aluno,
        "horario": horario,
        "linhas": linhas,
        "dias": dias,
        "mostrar_curso": mostrar_curso
    })

#====================================================
# DASHBOARD SECRETARIA
#====================================================






from django.db.models import Q



from .services import dados_financeiros_da_secretaria

@login_required
def dashboard_secretaria(request):

    # =========================================
    # VERIFICA SE É SECRETARIA
    # =========================================
    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard")

    # =========================================
    # ESCOLA
    # =========================================
    escola = getattr(request.user, "escola", None)

    if not escola:
        messages.error(
            request,
            "Nenhuma escola associada à secretaria."
        )

        return redirect("dashboard")

    # =========================================
    # ANO LETIVO ATIVO
    # =========================================
    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # =========================================
    # DADOS FINANCEIROS
    # =========================================
    context = dados_financeiros_da_secretaria(escola)

    # =========================================
    # DADOS EXTRAS DASHBOARD
    # =========================================
    context.update({

        "escola": escola,

        "ano_letivo": ano_letivo,

        "nome_secretaria":
            request.user.get_full_name()
            or request.user.username,

    })

    # =========================================
    # TEMPLATE
    # =========================================
    return render(
        request,
        "dashboard_secretaria.html",
        context
    )



@login_required
def cadastrar_secretaria(request):

    # =====================================================
    # PERMISSÃO
    # =====================================================

    if getattr(request.user, "role", None) != "DIRETOR":
        return redirect("dashboard")

    escola = getattr(request.user, "escola", None)

    if not escola:
        messages.error(
            request,
            "O Diretor precisa estar vinculado a uma escola."
        )
        return redirect("dashboard")

    if request.method == "POST":

        nome = request.POST.get("nome", "").strip()
        username = request.POST.get("username", "").strip()
        telefone = request.POST.get("telefone", "").strip()
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "").strip()
        role = request.POST.get("role", "").strip()

        # =====================================================
        # VALIDAÇÕES
        # =====================================================

        if not all([
            nome,
            username,
            telefone,
            senha,
            role,
        ]):
            messages.error(
                request,
                "Preencha todos os campos obrigatórios."
            )
            return redirect("cadastrar_secretaria")

        if role not in [
            "DIRETOR_PEDAGOGICO",
            "SECRETARIA",
            "FINANCEIRO",
        ]:
            messages.error(
                request,
                "Função inválida."
            )
            return redirect("cadastrar_secretaria")

        if len(senha) < 6:
            messages.error(
                request,
                "A senha deve possuir pelo menos 6 caracteres."
            )
            return redirect("cadastrar_secretaria")

        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                "Este nome de utilizador já existe."
            )
            return redirect("cadastrar_secretaria")

        if User.objects.filter(telefone=telefone).exists():
            messages.error(
                request,
                "Este telefone já está associado a outro utilizador."
            )
            return redirect("cadastrar_secretaria")

        if email and User.objects.filter(email=email).exists():
            messages.error(
                request,
                "Este e-mail já está associado a outro utilizador."
            )
            return redirect("cadastrar_secretaria")

        # =====================================================
        # CRIAR UTILIZADOR
        # =====================================================

        try:

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    telefone=telefone,
                    password=senha,
                    first_name=nome,
                    role=role,
                    escola=escola,
                )

                user.is_active = True
                user.save(update_fields=["is_active"])

            mensagens = {
                "DIRETOR_PEDAGOGICO": "Diretor Pedagógico cadastrado com sucesso.",
                "SECRETARIA": "Secretária cadastrada com sucesso.",
                "FINANCEIRO": "Utilizador do setor financeiro cadastrado com sucesso.",
            }

            messages.success(
                request,
                mensagens.get(role, "Utilizador cadastrado com sucesso.")
            )

            return redirect("dashboard")

        except Exception as e:

            messages.error(
                request,
                f"Erro ao cadastrar utilizador: {str(e)}"
            )

            return redirect("cadastrar_secretaria")

    return render(
        request,
        "cadastrar_secretaria.html"
    )


# ======================================================
    # DASHBOARD DIRETOR PEDAGOGICO
# ======================================================
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from academic.models import (
    Turma,
    Professor,
    Disciplina,
    Curso,
    Horario,
    Aluno
)


@login_required
def dashboard_diretor_pedagogico(request):

    # ======================================================
    # PERMISSÃO
    # ======================================================
    if request.user.role != "DIRETOR_PEDAGOGICO":
        messages.error(request, "Acesso negado.")
        return redirect("dashboard")

    escola = request.user.escola

    if not escola:
        messages.error(request, "Usuário não está vinculado a uma escola.")
        return redirect("dashboard")

    # ======================================================
    # ESTATÍSTICAS DO PAINEL
    # ======================================================
    total_turmas = Turma.objects.filter(escola=escola).count()

    total_professores = Professor.objects.filter(
        escola=escola
    ).count()

    total_disciplinas = Disciplina.objects.filter(
        escola=escola
    ).count()

    total_cursos = Curso.objects.filter(
        escola=escola
    ).count()

    total_horarios = Horario.objects.filter(
        turma__escola=escola
    ).count()


    total_alunos = Aluno.objects.filter(
        escola=escola
    ).count()

    # ======================================================
    # CONTEXTO
    # ======================================================
    context = {
        "escola": escola,
        "total_turmas": total_turmas,
        "total_professores": total_professores,
        "total_disciplinas": total_disciplinas,
        "total_cursos": total_cursos,
        "total_horarios": total_horarios,
        "total_alunos": total_alunos,
    }

    return render(request, "dashboard_pedagogico.html", context)


from django.shortcuts import render, redirect, get_object_or_404
from academic.models import Notificacao

def notificacoes(request):

    notificacoes = Notificacao.objects.filter(
        usuario=request.user
    ).order_by("-criada_em")

    nao_lidas = notificacoes.filter(lida=False).count()

    return render(request, "notificacoes.html", {
        "notificacoes": notificacoes,
        "nao_lidas": nao_lidas
    })


from django.http import JsonResponse

def marcar_notificacao_lida(request, id):

    notif = get_object_or_404(Notificacao, id=id, usuario=request.user)
    notif.lida = True
    notif.save()

    return JsonResponse({"success": True})

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def enviar_notificacao_realtime(notificacao):

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "notificacoes_global",
        {
            "type": "send_notification",
            "titulo": notificacao.titulo,
            "mensagem": notificacao.mensagem,
            "tipo": notificacao.tipo,
        }
    )

# =========================================================
# REGISTRAR PAGAMENTO
# =========================================================

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

@login_required
def registrar_pagamento(request):

    # =====================================================
    # PERMISSÃO
    # =====================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # =====================================================
    # CONFIGURAÇÃO FINANCEIRA
    # =====================================================

    config, _ = ConfiguracaoFinanceira.objects.get_or_create(
        escola=escola
    )

    # =====================================================
    # DADOS INICIAIS
    # =====================================================

    aluno = None

    numero_processo = ""

    tipo_pagamento = ""

    meses_lista = [
        "Janeiro", "Fevereiro", "Março", "Abril",
        "Maio", "Junho", "Julho", "Agosto",
        "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    valores_pagamentos = {

        "MATRICULA": float(config.valor_matricula or 0),

        "MULTA": float(config.valor_multa_mensalidade or 0),

        "DECLARACAO": float(config.valor_declaracao or 0),

        "EXAME": float(config.valor_exame or 0),

    }

    # =====================================================
    # FUNÇÃO AUXILIAR
    # =====================================================

    def render_page():

        return render(request, "registrar_pagamento.html", {

            "aluno": aluno,

            "numero_processo": numero_processo,

            "tipo_pagamento": tipo_pagamento,

            "meses_lista": meses_lista,

            "config": config,

            "valores_pagamentos": valores_pagamentos,

        })

    # =====================================================
    # BUSCAR ALUNO
    # =====================================================

    if request.method == "POST" and "buscar_aluno" in request.POST:

        numero_processo = request.POST.get(
            "numero_processo",
            ""
        ).strip()

        if not numero_processo:

            messages.error(
                request,
                "Informe o número de processo."
            )

            return render_page()

        aluno = Aluno.objects.select_related(
            "usuario",
            "turma",
            "curso",
            "ano_letivo"
        ).filter(
            numero_processo=numero_processo,
            escola=escola
        ).first()

        if not aluno:

            messages.error(
                request,
                "Aluno não encontrado."
            )

            return render_page()

        return render_page()

    # =====================================================
    # CONFIRMAR PAGAMENTO
    # =====================================================

    if request.method == "POST" and "confirmar_pagamento" in request.POST:

        aluno_id = request.POST.get("aluno_id")

        numero_processo = request.POST.get(
            "numero_processo",
            ""
        ).strip()

        tipo_pagamento = request.POST.get(
            "tipo_pagamento"
        )

        forma_pagamento = request.POST.get(
            "forma_pagamento"
        )

        observacao = request.POST.get(
            "observacao",
            ""
        ).strip()

        referencia = request.POST.get(
            "referencia",
            ""
        ).strip()

        valor_pago = request.POST.get(
            "valor_pago"
        )

        meses = request.POST.getlist("meses")

        # =====================================================
        # VALIDAR ALUNO
        # =====================================================

        if not aluno_id:

            messages.error(
                request,
                "Aluno inválido."
            )

            return redirect("registrar_pagamento")

        aluno = get_object_or_404(

            Aluno.objects.select_related(
                "usuario",
                "turma",
                "curso",
                "ano_letivo"
            ),

            id=aluno_id,
            escola=escola

        )

        # =====================================================
        # PAGAMENTO MENSALIDADE
        # =====================================================

        if tipo_pagamento == "MENSALIDADE":

            if not meses:

                messages.error(
                    request,
                    "Selecione pelo menos um mês."
                )

                return render_page()

            pagamentos_ids = []

            pagamentos_criados = 0

            with transaction.atomic():

                for mes in meses:

                    mensalidade = Mensalidade.objects.filter(
                        aluno=aluno,
                        mes=mes
                    ).first()

                    if not mensalidade:
                        continue

                    mensalidade.atualizar_status()

                    mensalidade.refresh_from_db()

                    if mensalidade.status == "PAGA":
                        continue

                    pagamento = Pagamento.objects.create(

                        aluno=aluno,

                        escola=escola,

                        mensalidade=mensalidade,

                        ano_letivo=mensalidade.ano_letivo,

                        tipo="MENSALIDADE",

                        valor_pago=mensalidade.valor,

                        forma_pagamento=forma_pagamento,

                        referencia=referencia,

                        observacao=observacao,

                        recebido_por=request.user,

                        data_pagamento=timezone.now()

                    )

                    pagamentos_ids.append(
                        pagamento.id
                    )

                    mensalidade.atualizar_status()

                    MovimentoCaixa.objects.create(

                        escola=escola,

                        tipo="ENTRADA",

                        descricao=(
                            f"Mensalidade {mes} - "
                            f"{aluno.usuario.get_full_name()}"
                        ),

                        valor=mensalidade.valor,

                        usuario=request.user,

                        origem="SECRETARIA"

                    )

                    pagamentos_criados += 1

            if pagamentos_criados <= 0:

                messages.warning(
                    request,
                    "Nenhuma mensalidade disponível para pagamento."
                )

                return render_page()

            request.session["recibos_ids"] = pagamentos_ids

            messages.success(

                request,

                f"{pagamentos_criados} pagamento(s) "
                f"registrado(s) com sucesso."

            )

            return redirect("recibo_pagamento")

        # =====================================================
        # OUTROS PAGAMENTOS
        # =====================================================

        valores_config = {

            "MATRICULA": config.valor_matricula,

            "MULTA": config.valor_multa_mensalidade,

            "EXAME": config.valor_exame,

            "DECLARACAO": config.valor_declaracao,

        }

        valor_configurado = valores_config.get(
            tipo_pagamento
        )

        if valor_configurado:

            valor_pago = valor_configurado

        else:

            if not valor_pago:

                messages.error(
                    request,
                    "Informe o valor do pagamento."
                )

                return render_page()

            try:

                valor_pago = Decimal(valor_pago)

            except (InvalidOperation, TypeError):

                messages.error(
                    request,
                    "Valor inválido."
                )

                return render_page()

        # =====================================================
        # ANO LETIVO
        # =====================================================

        ano_letivo = AnoLetivo.objects.filter(
            escola=escola,
            ativo=True
        ).first()

        if not ano_letivo:

            messages.error(
                request,
                "Nenhum ano letivo ativo encontrado."
            )

            return render_page()

        # =====================================================
        # CRIAR PAGAMENTO
        # =====================================================

        pagamento = Pagamento.objects.create(

            aluno=aluno,

            escola=escola,

            ano_letivo=ano_letivo,

            tipo=tipo_pagamento,

            valor_pago=valor_pago,

            forma_pagamento=forma_pagamento,

            referencia=referencia,

            observacao=observacao,

            recebido_por=request.user,

            data_pagamento=timezone.now()

        )

        # =====================================================
        # MOVIMENTO DE CAIXA
        # =====================================================

        MovimentoCaixa.objects.create(

            escola=escola,

            tipo="ENTRADA",

            descricao=(
                f"{tipo_pagamento} - "
                f"{aluno.usuario.get_full_name()}"
            ),

            valor=valor_pago,

            usuario=request.user,

            origem="SECRETARIA"

        )

        # =====================================================
        # RECIBO
        # =====================================================

        request.session["recibos_ids"] = [
            pagamento.id
        ]

        messages.success(
            request,
            "Pagamento registrado com sucesso."
        )

        return redirect("recibo_pagamento")

    return render_page()




# ==========================================
# LISTAS
# ==========================================

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect

MESES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro"
]

STATUS = [
    ("PENDENTE", "Pendente"),
    ("PAGA", "Paga"),
    ("ATRASADA", "Atrasada"),
]

@login_required
def lista_mensalidades(request):

    # =====================================================
    # PERMISSÃO
    # =====================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # =====================================================
    # FILTROS
    # =====================================================

    numero_processo = request.GET.get("numero_processo", "").strip()
    mes = request.GET.get("mes", "").strip()
    status = request.GET.get("status", "").strip()

    # =====================================================
    # QUERY BASE
    # =====================================================

    mensalidades = (
        Mensalidade.objects
        .filter(aluno__escola=escola)
        .select_related(
            "aluno",
            "aluno__turma",
            "ano_letivo"
        )
        .prefetch_related("pagamentos")
        .annotate(
            total_pago_calculado=Sum("pagamentos__valor_pago")
        )
        .order_by("vencimento")
    )

    aluno = None

    # =====================================================
    # FILTRO POR PROCESSO
    # =====================================================

    if numero_processo:

        aluno = (
            Aluno.objects
            .filter(
                numero_processo=numero_processo,
                escola=escola
            )
            .select_related(
                "usuario",
                "turma"
            )
            .first()
        )

        if aluno:

            mensalidades = mensalidades.filter(
                aluno=aluno
            )

        else:

            mensalidades = Mensalidade.objects.none()

    else:

        # Não mostrar tudo sem pesquisar
        mensalidades = Mensalidade.objects.none()

    # =====================================================
    # FILTRO MÊS
    # =====================================================

    if mes:

        mensalidades = mensalidades.filter(
            mes__iexact=mes
        )

    # =====================================================
    # ATUALIZA STATUS AUTOMATICAMENTE
    # =====================================================

    mensalidades_list = []

    for mensalidade in mensalidades:
        total_pago = getattr(
            mensalidade,
            "total_pago_calculado",
            Decimal("0.00")
        ) or Decimal("0.00")

        # Atualiza status usando método do model
        mensalidade.atualizar_status()

        # Atualiza objeto em memória
        mensalidade.refresh_from_db(fields=["status"])

        # Valores auxiliares
        mensalidade.total_pago_display = total_pago

        mensalidade.valor_restante = (
                mensalidade.valor - total_pago
        )

        mensalidade.percentual_pago = int(
            (total_pago / mensalidade.valor) * 100
        ) if mensalidade.valor > 0 else 0

        mensalidades_list.append(mensalidade)

    # =====================================================
    # FILTRO STATUS
    # =====================================================

    if status:

        mensalidades_list = [
            m for m in mensalidades_list
            if m.status == status
        ]

    # =====================================================
    # CONTADORES
    # =====================================================

    total_mensalidades = len(mensalidades_list)

    total_pago_geral = sum(
        m.total_pago_display
        for m in mensalidades_list
    )

    total_divida = sum(
        m.restante
        for m in mensalidades_list
    )

    pendentes = len([
        m for m in mensalidades_list
        if m.status == "PENDENTE"
    ])

    atrasadas = len([
        m for m in mensalidades_list
        if m.status == "ATRASADA"
    ])

    pagas = len([
        m for m in mensalidades_list
        if m.status == "PAGA"
    ])

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "mensalidades": mensalidades_list,

        "numero_processo": numero_processo,

        "mes": mes,

        "status": status,

        "aluno": aluno,

        "meses": MESES,

        "status_options": STATUS,

        # DASHBOARD
        "total_mensalidades": total_mensalidades,

        "total_pago_geral": total_pago_geral,

        "total_divida": total_divida,

        "pendentes": pendentes,

        "atrasadas": atrasadas,

        "pagas": pagas,
    }

    return render(
        request,
        "mensalidades.html",
        context
    )




# ==========================================================
# LISTA DE PAGAMENTOS
# ==========================================================

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import render, redirect

@login_required
def lista_pagamentos(request):

    # ==========================================================
    # PERMISSÃO
    # ==========================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # ==========================================================
    # FILTROS
    # ==========================================================

    numero_processo = request.GET.get("numero_processo", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    forma = request.GET.get("forma", "").strip()
    data = request.GET.get("data", "").strip()

    # ==========================================================
    # QUERY
    # ==========================================================

    pagamentos = Pagamento.objects.select_related(
        "aluno",
        "aluno__usuario",
        "mensalidade",
        "ano_letivo",
        "recebido_por"
    ).filter(
        escola=escola
    ).order_by("-data_pagamento")

    # ==========================================================
    # FILTRO PROCESSO
    # ==========================================================

    if numero_processo:

        pagamentos = pagamentos.filter(
            aluno__numero_processo__icontains=numero_processo
        )

    # ==========================================================
    # FILTRO TIPO
    # ==========================================================

    if tipo:

        pagamentos = pagamentos.filter(tipo=tipo)

    # ==========================================================
    # FILTRO FORMA PAGAMENTO
    # ==========================================================

    if forma:

        pagamentos = pagamentos.filter(
            forma_pagamento=forma
        )

    # ==========================================================
    # FILTRO DATA
    # ==========================================================

    if data:

        pagamentos = pagamentos.filter(
            data_pagamento__date=data
        )

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    total_recebido = pagamentos.aggregate(
        total=Sum("valor_pago")
    )["total"] or 0

    total_pagamentos = pagamentos.aggregate(
        total=Count("id")
    )["total"] or 0

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {

        "pagamentos": pagamentos,

        "total_recebido": total_recebido,

        "total_pagamentos": total_pagamentos,

        "numero_processo": numero_processo,

        "tipo": tipo,

        "forma": forma,

        "data": data,

        "tipos_pagamento": Pagamento.TIPOS,

        "formas_pagamento": Pagamento.FORMAS_PAGAMENTO,

    }

    return render(
        request,
        "pagamentos.html",
        context
    )




from academic.models import Mensalidade

@login_required
def notas_aluno(request):

    # =========================================
    # BUSCAR ALUNO
    # =========================================

    aluno = get_object_or_404(
        Aluno.objects.select_related(
            "turma",
            "turma__ano_letivo",
            "turma__escola"
        ),
        usuario=request.user
    )

    # =========================================
    # ANO LETIVO ATIVO
    # =========================================

    ano_letivo = AnoLetivo.objects.filter(
        escola=aluno.escola,
        ativo=True
    ).first()

    # FALLBACK
    if not ano_letivo and aluno.turma:
        ano_letivo = aluno.turma.ano_letivo

    # =========================================
    # VERIFICAR MENSALIDADES ATRASADAS
    # =========================================

    tem_atrasada = Mensalidade.objects.filter(
        aluno=aluno,
        status="ATRASADA"
    ).exists()

    if tem_atrasada:

        messages.error(
            request,
            "Você possui mensalidades em atraso. Regularize o pagamento para visualizar o boletim."
        )

        return render(
            request,
            "nota_aluno.html",
            {
                "bloqueado": True,
                "aluno": aluno,
                "ano_letivo": ano_letivo
            }
        )

    # =========================================
    # BUSCAR NOTAS APENAS DO ANO ATIVO
    # =========================================

    notas = (
        Nota.objects
        .filter(
            aluno=aluno,
            ano_letivo=ano_letivo
        )
        .select_related(
            "disciplina",
            "ano_letivo"
        )
        .order_by(
            "disciplina__nome",
            "trimestre"
        )
    )

    # =========================================
    # ORGANIZAR DISCIPLINAS
    # =========================================

    disciplinas = {}

    for nota in notas:

        nome = nota.disciplina.nome

        if nome not in disciplinas:

            disciplinas[nome] = {

                1: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                2: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                3: {
                    "p1": None,
                    "p2": None,
                    "media": None
                },

                "media_final": None
            }

        p1 = nota.p1
        p2 = nota.p2

        media = None

        if p1 is not None or p2 is not None:

            v1 = float(p1 or 0)
            v2 = float(p2 or 0)

            media = round((v1 + v2) / 2, 1)

        disciplinas[nome][nota.trimestre] = {

            "p1": p1,
            "p2": p2,
            "media": media
        }

    # =========================================
    # CALCULAR MÉDIA FINAL
    # =========================================

    for disciplina, dados in disciplinas.items():

        medias = []

        for t in [1, 2, 3]:

            if dados[t]["media"] is not None:

                medias.append(dados[t]["media"])

        if medias:

            dados["media_final"] = round(
                sum(medias) / len(medias),
                1
            )

    # =========================================
    # HISTÓRICO ACADÉMICO
    # =========================================

    historicos = HistoricoAcademico.objects.filter(
        aluno=aluno
    ).select_related(
        "ano_letivo",
        "turma"
    ).order_by("-criado_em")

    # =========================================
    # CONTEXT
    # =========================================

    context = {

        "aluno": aluno,
        "disciplinas": disciplinas,
        "bloqueado": False,
        "ano_letivo": ano_letivo,
        "historicos": historicos,
    }

    return render(
        request,
        "nota_aluno.html",
        context
    )


# ============================================================
#                VALIDAR BOLETIM VIA QR CODE
# ============================================================


def validar_boletim(request, codigo):

    boletim = Boletim.objects.select_related(
        "aluno",
        "aluno__usuario",
        "aluno__turma",
        "aluno__turma__escola"
    ).filter(codigo_validacao=codigo).first()

    if not boletim:
        return render(request, "boletim_invalido.html")

    aluno = boletim.aluno
    escola = aluno.turma.escola

    context = {
        "boletim": boletim,
        "aluno_nome": aluno.usuario.get_full_name() or aluno.usuario.username,
        "turma": f"{aluno.turma.classe}ª {aluno.turma.identificador}",
        "escola": escola.nome,
        "ano_letivo": aluno.turma.ano_letivo,
    }

    return render(request, "validar_boletim.html", context)


# ==========================================================
# CONFIRMAR MATRÍCULA
# ==========================================================

@login_required
def confirmar_matricula(request):

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard")

    escola = request.user.escola

    numero_processo = request.GET.get("numero_processo", "").strip()

    status = request.GET.get("status", "").strip()

    ano_letivo_ativo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # ======================================================
    # QUERY BASE
    # ======================================================

    alunos = Aluno.objects.select_related(
        "usuario",
        "turma",
        "ano_letivo"
    ).filter(
        escola=escola
    )

    # ======================================================
    # FILTRO POR PROCESSO
    # ======================================================

    if numero_processo:

        alunos = alunos.filter(
            numero_processo__icontains=numero_processo
        )

    # ======================================================
    # FILTRO STATUS
    # ======================================================

    if status == "pendente":

        alunos = alunos.filter(
            matricula_confirmada=False
        )

    elif status == "confirmado":

        alunos = alunos.filter(
            matricula_confirmada=True
        )

    # ======================================================
    # ORDENAÇÃO
    # ======================================================

    alunos = alunos.order_by(
        "classe",
        "numero_na_turma",
        "usuario__first_name"
    )

    # ======================================================
    # CONFIRMAR MATRÍCULA
    # ======================================================

    if request.method == "POST":

        aluno_id = request.POST.get("aluno_id")

        aluno = get_object_or_404(
            Aluno,
            id=aluno_id,
            escola=escola
        )

        # evita confirmação duplicada
        if aluno.matricula_confirmada:

            messages.warning(
                request,
                "A matrícula deste aluno já foi confirmada."
            )

            return redirect(
                f"{request.path}?numero_processo={aluno.numero_processo}"
            )

        # ======================================================
        # CONFIRMAR MATRÍCULA + HISTÓRICO
        # ======================================================

        HistoricoMatricula.objects.create(
            aluno=aluno,
            ano_letivo=ano_letivo_ativo,
            turma=aluno.turma,
            classe=aluno.classe,
            curso=aluno.curso,
            numero_na_turma=aluno.numero_na_turma,
            matricula=aluno.matricula,
            total_alunos_turma=Aluno.objects.filter(
                turma=aluno.turma,
                ano_letivo=ano_letivo_ativo
            ).count()
        )

        # depois sim confirma matrícula
        aluno.matricula_confirmada = True

        if hasattr(aluno, "precisa_confirmacao"):
            aluno.precisa_confirmacao = False

        if hasattr(aluno, "ultimo_ano_confirmado"):
            aluno.ultimo_ano_confirmado = ano_letivo_ativo

        aluno.save()

        messages.success(
            request,
            f"Matrícula do aluno "
            f"{aluno.usuario.get_full_name()} "
            f"confirmada com sucesso."
        )

        return redirect(
            f"{request.path}?numero_processo={aluno.numero_processo}"
        )

    # ======================================================
    # ESTATÍSTICAS
    # ======================================================

    alunos_confirmados = Aluno.objects.filter(
        escola=escola,
        matricula_confirmada=True
    ).count()

    alunos_pendentes = Aluno.objects.filter(
        escola=escola,
        matricula_confirmada=False
    ).count()

    context = {

        "alunos": alunos,

        "numero_processo": numero_processo,

        "status": status,

        "ano_letivo_ativo": ano_letivo_ativo,

        "alunos_confirmados": alunos_confirmados,

        "alunos_pendentes": alunos_pendentes,

    }

    return render(
        request,
        "confirmar_matricula.html",
        context
    )



# ==========================================================
# CRIAR MATRÍCULA
# ==========================================================

from decimal import Decimal
import random
import string

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)

User = get_user_model()


# ==========================================================
# USERNAME ÚNICO
# ==========================================================

def gerar_username_unico(nome):

    base = (
        nome.lower()
        .replace(" ", "")
        .replace(".", "")
    )

    username = base
    contador = 1

    while User.objects.filter(username=username).exists():

        username = f"{base}{contador}"

        contador += 1

    return username


# ==========================================================
# NÚMERO PROCESSO
# ==========================================================

def gerar_numero_processo(escola):

    ultimo_aluno = Aluno.objects.filter(
        escola=escola,
        numero_processo__isnull=False
    ).order_by("-id").first()

    if (
        ultimo_aluno
        and ultimo_aluno.numero_processo
        and ultimo_aluno.numero_processo.isdigit()
    ):

        novo_numero = str(
            int(ultimo_aluno.numero_processo) + 1
        ).zfill(6)

    else:

        novo_numero = "000001"

    return novo_numero


# ==========================================================
# SENHA AUTOMÁTICA
# ==========================================================

def gerar_senha():

    return ''.join(

        random.choices(

            string.ascii_letters + string.digits,

            k=8

        )

    )


# ==========================================================
# CRIAR MATRÍCULA
# ==========================================================

@login_required
@transaction.atomic
def criar_matricula(request):

    if request.user.role != "SECRETARIA":
        return redirect("dashboard")

    escola = request.user.escola

    if not escola:
        messages.error(request, "Usuário não vinculado a escola.")
        return redirect("dashboard")

    # ======================================================
    # PLANO + RESTRIÇÃO DE ALUNOS
    # ======================================================

    plano = getattr(escola, "plano", None)

    if not plano:
        messages.error(request, "A escola não possui um plano associado.")
        return redirect("dashboard")

    if not getattr(plano, "ativo", False):
        messages.error(request, "O plano da escola encontra-se inativo.")
        return redirect("dashboard")

    total_alunos = Aluno.objects.filter(
        escola=escola,
        ativo=True
    ).count()

    if total_alunos >= plano.limite_alunos:
        messages.error(
            request,
            f"O limite de {plano.limite_alunos} alunos "
                f"do Plano {plano.nome} foi atingido. "
                "Entre em contacto com a ICA Systems para atualizar o plano."
        )
        return redirect("dashboard")

    # Ano letivo ativo
    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        messages.error(request, "Nenhum ano letivo ativo.")
        return redirect("criar_matricula")

    if request.method == "POST":

        nome = request.POST.get("nome")
        email = request.POST.get("email")
        telefone = request.POST.get("telefone", "").strip()
        numero_bi = request.POST.get("numero_bi")
        data_nascimento = request.POST.get("data_nascimento")
        sexo = request.POST.get("sexo")
        turma_id = request.POST.get("turma")

        if not all([nome, telefone, numero_bi, data_nascimento, sexo, turma_id]):
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect("criar_matricula")

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola
        )

        if Aluno.objects.filter(numero_bi=numero_bi, escola=escola).exists():
            messages.error(request, "Já existe aluno com este BI.")
            return redirect("criar_matricula")

        if User.objects.filter(telefone=telefone).exists():
            messages.error(
                request,
                "Já existe um utilizador com este telefone."
            )
            return redirect("criar_matricula")

        senha_gerada = ''.join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )

        ultimo = Aluno.objects.filter(
            escola=escola,
            numero_processo__isnull=False
        ).order_by("-id").first()

        if ultimo and ultimo.numero_processo and ultimo.numero_processo.isdigit():
            numero_processo = str(int(ultimo.numero_processo) + 1).zfill(6)
        else:
            numero_processo = "000001"



        user = User.objects.create_user(
            username=numero_processo,
            password=senha_gerada,
            role="ALUNO",
            first_name=nome,
            email=email if email else "",
            telefone=telefone,
            escola=escola
        )



        numero_na_turma = (
            Aluno.objects.filter(
                turma=turma,
                ano_letivo=ano_letivo
            ).count() + 1
        )

        matricula = f"{turma.classe}{turma.identificador}-{numero_na_turma}"

        aluno = Aluno.objects.create(
            usuario=user,
            matricula=matricula,
            numero_processo=numero_processo,
            numero_bi=numero_bi,
            data_nascimento=data_nascimento,
            sexo=sexo,
            turma=turma,
            classe=turma.classe,
            ano_letivo=ano_letivo,
            numero_na_turma=numero_na_turma,
            matricula_confirmada=True,
            escola=escola,
        )

        config, created = ConfiguracaoFinanceira.objects.get_or_create(
            escola=escola
        )

        valor_mensalidade = config.obter_valor_mensalidade(aluno.classe)

        gerar_mensalidades_aluno(
            aluno=aluno,
            ano_letivo=ano_letivo,
            valor=valor_mensalidade
        )

        messages.success(
            request,
            (
                "Matrícula criada com sucesso!\n"
                f"Username: {numero_processo}\n"
                f"Senha inicial: {senha_gerada}"
            )
        )

        return redirect("criar_matricula")

    turmas = Turma.objects.filter(
        escola=escola
    ).select_related("curso").order_by(
        "classe",
        "identificador"
    )

    cursos = Curso.objects.filter(
        escola=escola
    )

    return render(request, "matricula.html", {
        "turmas": turmas,
        "cursos": cursos
    })



# =====================================================
# BLOQUEADO
# =====================================================

@login_required
def bloqueado(request):
    return render(request, 'bloqueado.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string


@login_required
def adicionar_aluno(request):

    escola = get_escola(request)

    if not escola:
        return redirect("escolas")

    if request.user.role != "SECRETARIA":
        return redirect("dashboard")

    plano = escola.plano

    if plano is None:
        messages.error(
            request,
            "A escola não possui um plano associado."
        )
        return redirect("dashboard")

    if not plano.ativo:
        messages.error(
            request,
            "O plano da escola encontra-se inativo."
        )
        return redirect("dashboard")

    total_alunos = Aluno.objects.filter(
        escola=escola,
        ativo=True
    ).count()

    if total_alunos >= plano.limite_alunos:
        messages.error(
            request,
            (
                f"O limite de {plano.limite_alunos} alunos "
                f"do Plano {plano.nome} foi atingido. "
                "Entre em contacto com a ICA Systems para atualizar o plano."
            )
        )
        return redirect("dashboard")

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        messages.error(
            request,
            "Nenhum ano letivo ativo encontrado."
        )
        return redirect("matricula")

    cursos = Curso.objects.filter(
        escola=escola
    ).order_by("nome")

    turmas = (
        Turma.objects
        .filter(escola=escola)
        .select_related("curso", "ano_letivo")
        .order_by("classe", "identificador")
    )

    if request.method == "POST":

        nome = request.POST.get("nome", "").strip()
        email = request.POST.get("email", "").strip()
        telefone = request.POST.get(
            "telefone",
            ""
        ).strip()
        numero_processo = request.POST.get(
            "numero_processo",
            ""
        ).strip()

        numero_bi = request.POST.get(
            "numero_bi",
            ""
        ).strip()

        data_nascimento = request.POST.get(
            "data_nascimento",
            ""
        ).strip()

        sexo = request.POST.get(
            "sexo",
            ""
        ).strip()

        turma_id = request.POST.get(
            "turma",
            ""
        ).strip()

        # ==========================
        # VALIDAÇÕES
        # ==========================

        if not nome:
            messages.error(request, "Nome obrigatório.")
            return redirect("adicionar_aluno")

        if not numero_processo:
            messages.error(request, "Número de processo obrigatório.")
            return redirect("adicionar_aluno")

        if not numero_bi:
            messages.error(request, "BI obrigatório.")
            return redirect("adicionar_aluno")

        if not data_nascimento:
            messages.error(request, "Data de nascimento obrigatória.")
            return redirect("adicionar_aluno")

        if not sexo:
            messages.error(request, "Sexo obrigatório.")
            return redirect("adicionar_aluno")

        if not telefone:
            messages.error(
                request,
                "Telefone obrigatório."
            )
            return redirect("adicionar_aluno")

        if not turma_id:
            messages.error(request, "Selecione a turma.")
            return redirect("adicionar_aluno")

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola
        )

        # Processo duplicado
        if Aluno.objects.filter(
            numero_processo=numero_processo,
            escola=escola
        ).exists():

            messages.error(
                request,
                "Já existe um aluno com este número de processo."
            )
            return redirect("adicionar_aluno")

        # BI duplicado
        if Aluno.objects.filter(
            numero_bi=numero_bi,
            escola=escola
        ).exists():

            messages.error(
                request,
                "Já existe um aluno com este BI."
            )
            return redirect("adicionar_aluno")

        if User.objects.filter(
                telefone=telefone
        ).exists():
            messages.error(
                request,
                "Já existe um utilizador com este telefone."
            )
            return redirect("adicionar_aluno")

        # Username = Nome
        if User.objects.filter(
            username=numero_processo
        ).exists():

            messages.error(
                request,
                "Já existe utilizador com este número de processo."
            )
            return redirect("adicionar_aluno")

        try:

            with transaction.atomic():

                # ==========================
                # SENHA AUTOMÁTICA
                # ==========================
                senha_gerada = get_random_string(
                    length=8
                )

                user = User.objects.create_user(
                    username=numero_processo,
                    email=email,
                    telefone=telefone,
                    password=senha_gerada,
                    first_name=nome,
                    role="ALUNO",
                    escola=escola
                )

                # ==========================
                # Nº na turma
                # ==========================
                numero_na_turma = (
                    Aluno.objects.filter(
                        turma=turma
                    ).count() + 1
                )

                # ==========================
                # Matrícula inteligente
                # Ex: 2026-10A-0005
                # ==========================
                matricula = (
                    f"{ano_letivo.id}-"
                    f"{turma.classe}"
                    f"{turma.identificador}-"
                    f"{str(numero_na_turma).zfill(4)}"
                )

                aluno = Aluno.objects.create(
                    usuario=user,
                    matricula=matricula,
                    numero_processo=numero_processo,
                    numero_na_turma=numero_na_turma,
                    numero_bi=numero_bi,
                    data_nascimento=data_nascimento,
                    sexo=sexo,
                    turma=turma,
                    classe=turma.classe,
                    ano_letivo=ano_letivo,

                    # Primeira matrícula já confirmada
                    matricula_confirmada=True,

                    escola=escola
                )

                # ==========================
                # Geração mensalidades
                # ==========================
                config, created = ConfiguracaoFinanceira.objects.get_or_create(
                    escola=escola
                )

                valor_mensalidade = config.obter_valor_mensalidade(aluno.classe)

                gerar_mensalidades_aluno(
                    aluno=aluno,
                    ano_letivo=ano_letivo,
                    valor=valor_mensalidade
                )

            messages.success(
                request,
                (
                    f"Aluno cadastrado com sucesso. "
                    f"Username: {numero_processo} | "
                    f"Senha inicial: {senha_gerada}"
                )
            )

            return redirect("criar_matricula")

        except Exception as e:

            messages.error(
                request,
                f"Erro ao cadastrar aluno: {str(e)}"
            )

            return redirect("adicionar_aluno")

    return render(
        request,
        "adicionar_aluno.html",
        {
            "turmas": turmas,
            "cursos": cursos,
        }
    )



@login_required
def painel_diretor_alunos(request):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    escola = get_escola(request)

    alunos = Aluno.objects.filter(
        escola=escola
    ).select_related("turma", "usuario").order_by("turma", "numero_na_turma")

    return render(request, "alunos.html", {
        "alunos": alunos
    })



@login_required
def eliminar_professor(request, id):

    if getattr(request.user, "role", None) != "DIRETOR":
        return redirect("dashboard")

    professor = get_object_or_404(User, id=id, role="PROFESSOR")

    if request.method == "POST":
        professor.delete()  # apaga também o user
        messages.success(request, "Professor eliminado com sucesso!")

    return redirect("professores")


@login_required
def nova_mensalidade(request):
    return render(request, "nova_mensalidade.html")


@login_required
def buscar_aluno_por_processo(request):
    numero_processo = request.GET.get("processo")

    try:
        aluno = Aluno.objects.get(numero_processo=numero_processo)
        return JsonResponse({
            "sucesso": True,
            "id": aluno.id,
            "nome": aluno.usuario.get_full_name()
        })
    except Aluno.DoesNotExist:
        return JsonResponse({
            "sucesso": False
        })





@login_required
def lista_secretarias(request):
    """
    Lista os utilizadores administrativos da escola
    (Diretor Pedagógico, Secretaria e Financeiro).
    """

    if request.user.role == "SUPERADMIN":
        secretarias = User.objects.filter(
            role__in=[
                "DIRETOR_PEDAGOGICO",
                "SECRETARIA",
                "FINANCEIRO",
            ]
        ).order_by("first_name", "last_name")

    else:
        secretarias = User.objects.filter(
            escola=request.user.escola,
            role__in=[
                "DIRETOR_PEDAGOGICO",
                "SECRETARIA",
                "FINANCEIRO",
            ]
        ).order_by("first_name", "last_name")

    return render(
        request,
        "lista_secretarias.html",
        {
            "secretarias": secretarias,
        },
    )


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render


@login_required
def eliminar_secretaria(request, id):
    """
    Permite ao Diretor eliminar Diretores Pedagógicos,
    Secretarias e Financeiros da sua escola.
    """

    if request.user.role != "DIRETOR":
        messages.error(request, "Você não tem permissão para esta ação.")
        return redirect("dashboard")

    utilizador = get_object_or_404(
        User,
        id=id,
        escola=request.user.escola,
        role__in=[
            "DIRETOR_PEDAGOGICO",
            "SECRETARIA",
            "FINANCEIRO",
        ],
    )

    # Impede eliminar a própria conta
    if utilizador.id == request.user.id:
        messages.error(request, "Não é permitido eliminar a sua própria conta.")
        return redirect("lista_secretarias")

    if request.method == "POST":
        nome = utilizador.get_full_name() or utilizador.username
        utilizador.delete()

        messages.success(
            request,
            f'O utilizador "{nome}" foi eliminado com sucesso.'
        )

        return redirect("lista_secretarias")

    return render(
        request,
        "eliminar_secretaria.html",
        {
            "secretaria": utilizador,
        },
    )


def imprimir_lista_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id)
    alunos = turma.alunos.all().order_by("usuario__first_name")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="lista_'
        f'{turma.classe}_{turma.identificador}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    elementos = []

    styles = getSampleStyleSheet()

    # Título
    titulo = Paragraph(
        f"<b>Lista de Alunos - {turma.get_classe_display()} "
        f"{turma.identificador}</b>",
        styles['Title']
    )
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.4 * inch))

    # Informações
    info = Paragraph(
        f"Ano Letivo: {turma.ano_letivo}<br/>"
        f"Escola: {turma.escola.nome}<br/>"
        f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles['Normal']
    )
    elementos.append(info)
    elementos.append(Spacer(1, 0.4 * inch))

    # Cabeçalho
    dados = [["Nº",
              "Nome do Aluno",
              "Nº Processo",
              "Sexo",
              "Nº BI",
              "Data Nascimento"]]

    for index, aluno in enumerate(alunos, start=1):
        dados.append([
            str(index),
            aluno.usuario.get_full_name(),
            aluno.numero_processo,
            aluno.get_sexo_display() if hasattr(aluno, "get_sexo_display") else aluno.sexo,
            aluno.numero_bi if aluno.numero_bi else "-",
            aluno.data_nascimento.strftime("%d/%m/%Y") if aluno.data_nascimento else "-"
        ])

    tabela = Table(dados,
                   colWidths=[30, 150, 70, 50, 90, 90],
                   repeatRows=1)

    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 0.4 * inch))

    total = Paragraph(
        f"<b>Total de Alunos: {alunos.count()}</b>",
        styles['Normal']
    )
    elementos.append(total)

    doc.build(elementos)

    return response




from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from datetime import datetime
@login_required
@transaction.atomic

def promover_ano_letivo(request, ano_id):

    if request.method != "POST":
        return redirect("dashboard")

    escola = request.user.escola

    ano_atual = get_object_or_404(
        AnoLetivo,
        id=ano_id,
        escola=escola
    )

    # =========================
    # CRIAR NOVO ANO
    # =========================

    try:
        inicio, fim = ano_atual.nome.split("/")
        novo_nome = f"{int(inicio)+1}/{int(fim)+1}"
    except:
        messages.error(request, "Formato do ano letivo inválido.")
        return redirect("dashboard")

    # Desativar anos anteriores
    AnoLetivo.objects.filter(
        escola=escola
    ).update(ativo=False)

    # Criar novo ano
    novo_ano, criado = AnoLetivo.objects.get_or_create(
        nome=novo_nome,
        escola=escola,
        defaults={
            "ativo": True
        }
    )

    novo_ano.ativo = True
    novo_ano.save()

    promovidos = 0
    finalistas = 0

    # =========================
    # TURMAS DO ANO ATUAL
    # =========================

    turmas = Turma.objects.filter(
        ano_letivo=ano_atual,
        escola=escola
    )

    for turma in turmas:

        alunos = turma.alunos.all()

        for aluno in alunos:

            classe_atual = int(turma.classe)

            # =========================
            # FINALISTA
            # =========================

            if classe_atual >= 12:

                HistoricoAcademico.objects.create(
                    aluno=aluno,
                    ano_letivo=ano_atual,
                    classe=turma.classe,
                    turma=turma,
                    situacao="FINALISTA"
                )

                finalistas += 1
                continue

            # =========================
            # NOVA CLASSE
            # =========================

            nova_classe = str(classe_atual + 1)

            # =========================
            # CRIAR NOVA TURMA
            # =========================

            nova_turma, created = Turma.objects.get_or_create(

                classe=nova_classe,

                identificador=turma.identificador,

                turno=turma.turno,

                curso=turma.curso,

                ano_letivo=novo_ano,

                escola=turma.escola,

                defaults={
                    "professor": turma.professor
                }
            )

            # =========================
            # HISTÓRICO
            # =========================

            HistoricoAcademico.objects.create(
                aluno=aluno,
                ano_letivo=ano_atual,
                classe=turma.classe,
                turma=turma,
                situacao="APROVADO"
            )

            # =========================
            # PROMOVER ALUNO
            # =========================

            aluno.classe = nova_classe
            aluno.ano_letivo = novo_ano
            aluno.turma = nova_turma

            aluno.save()

            promovidos += 1

    # =========================
    # PDF
    # =========================

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from django.http import HttpResponse
    from django.utils import timezone

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="encerramento_{ano_atual.nome}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()

    titulo = styles["Title"]
    titulo.alignment = TA_CENTER

    subtitulo = styles["Heading2"]
    subtitulo.alignment = TA_CENTER

    elementos = []

    # =====================================================
    # CABEÇALHO
    # =====================================================

    nome_escola = (
        request.user.escola.nome
        if getattr(request.user, "escola", None)
        else "Sistema Eduscore"
    )

    elementos.append(
        Paragraph("<b>EDUSCORE</b>", titulo)
    )

    elementos.append(
        Paragraph(nome_escola, subtitulo)
    )

    elementos.append(Spacer(1, 0.20 * inch))

    elementos.append(
        Paragraph(
            f"<b>RELATÓRIO DE ENCERRAMENTO DO ANO LETIVO {ano_atual.nome}</b>",
            styles["Heading1"],
        )
    )

    elementos.append(Spacer(1, 0.35 * inch))

    # =====================================================
    # TABELA RESUMO
    # =====================================================

    dados = [
        ["Campo", "Informação"],
        ["Ano Letivo Encerrado", str(ano_atual.nome)],
        ["Novo Ano Letivo", str(novo_nome)],
        ["Alunos Promovidos", str(promovidos)],
        ["Finalistas", str(finalistas)],
        [
            "Emitido em",
            timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        ],
        [
            "Emitido por",
            request.user.get_full_name() or request.user.username,
        ],
    ]

    tabela = Table(
        dados,
        colWidths=[220, 250],
    )

    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela)

    elementos.append(Spacer(1, 0.35 * inch))

    # =====================================================
    # MENSAGEM
    # =====================================================

    elementos.append(
        Paragraph(
            (
                "O encerramento do ano letivo foi realizado com sucesso. "
                "Os alunos elegíveis foram promovidos para o novo ano letivo "
                "e os finalistas concluíram o seu ciclo académico."
            ),
            styles["Normal"],
        )
    )

    elementos.append(Spacer(1, 0.60 * inch))

    # =====================================================
    # ASSINATURA
    # =====================================================

    elementos.append(
        Paragraph(
            "__________________________________________",
            styles["Normal"],
        )
    )

    elementos.append(
        Paragraph(
            "Direção da Escola",
            styles["Normal"],
        )
    )

    elementos.append(Spacer(1, 0.40 * inch))

    # =====================================================
    # RODAPÉ
    # =====================================================

    elementos.append(
        Paragraph(
            "<font size='8' color='grey'>"
            "Documento gerado automaticamente pelo Sistema Eduscore. "
            "Este relatório serve como comprovativo do encerramento do ano letivo."
            "</font>",
            styles["Normal"],
        )
    )

    # Gerar PDF
    doc.build(elementos)

    # Mensagem de sucesso
    messages.success(
        request,
        f"{promovidos} alunos promovidos para {novo_nome}.",
    )

    return response


from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from datetime import datetime
from io import BytesIO


@login_required
@transaction.atomic
def promover_alunos(request, ano_id):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("dashboard")

    escola = request.user.escola

    # ======================================
    # VALIDAR SENHA
    # ======================================
    senha = request.POST.get("senha_confirmacao")

    if not request.user.check_password(senha):
        messages.error(request, "Senha incorreta.")
        return redirect("dashboard")

    # ======================================
    # ANO LETIVO ATUAL
    # ======================================
    ano_letivo = AnoLetivo.objects.filter(
        id=ano_id,
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        messages.error(request, "Ano letivo não encontrado.")
        return redirect("dashboard")

    # ======================================
    # NOVO ANO LETIVO
    # ======================================
    try:
        inicio, fim = ano_letivo.nome.split("/")
        novo_nome = f"{int(inicio)+1}/{int(fim)+1}"
    except:
        messages.error(request, "Formato do ano letivo inválido.")
        return redirect("dashboard")

    novo_ano, _ = AnoLetivo.objects.get_or_create(
        escola=escola,
        nome=novo_nome,
        defaults={"ativo": True}
    )

    AnoLetivo.objects.filter(escola=escola).update(ativo=False)
    novo_ano.ativo = True
    novo_ano.save()

    # ======================================
    # CONTADORES
    # ======================================
    promovidos = 0
    reprovados = 0
    finalistas = 0

    # ======================================
    # ALUNOS
    # ======================================
    alunos = Aluno.objects.filter(
        escola=escola,
        ano_letivo=ano_letivo
    ).select_related("turma", "curso", "usuario")

    for aluno in alunos:

        media = calcular_media_anual(aluno, ano_letivo)
        turma_atual = aluno.turma

        # ======================================
        # HISTÓRICO MATRÍCULA
        # ======================================
        quantidade_alunos = Aluno.objects.filter(
            turma=turma_atual,
            ano_letivo=ano_letivo
        ).count()

        HistoricoMatricula.objects.create(
            aluno=aluno,
            ano_letivo=ano_letivo,
            turma=turma_atual,
            classe=aluno.classe,
            curso=aluno.curso,
            matricula=aluno.matricula,
            numero_na_turma=aluno.numero_na_turma,
            total_alunos_turma=quantidade_alunos,
            media_final=media,
            aprovado=(media >= 10)
        )

        try:
            classe_atual = int(aluno.classe)
        except:
            continue

        # ======================================
        # REPROVADO
        # ======================================
        if media < 10:

            HistoricoAcademico.objects.create(
                aluno=aluno,
                ano_letivo=ano_letivo,
                classe=aluno.classe,
                turma=turma_atual,
                curso=aluno.curso,
                media_final=media,
                situacao="REPROVADO"
            )

            aluno.precisa_confirmacao = True
            aluno.matricula_confirmada = False
            aluno.aprovado = False
            aluno.save()

            reprovados += 1
            continue

        # ======================================
        # FINALISTA
        # ======================================
        if classe_atual >= 13:

            HistoricoAcademico.objects.create(
                aluno=aluno,
                ano_letivo=ano_letivo,
                classe=aluno.classe,
                turma=turma_atual,
                curso=aluno.curso,
                media_final=media,
                situacao="FINALISTA"
            )

            aluno.ativo = False
            aluno.aprovado = True
            aluno.save()

            finalistas += 1
            continue

        # ======================================
        # APROVADO
        # ======================================
        HistoricoAcademico.objects.create(
            aluno=aluno,
            ano_letivo=ano_letivo,
            classe=aluno.classe,
            turma=turma_atual,
            curso=aluno.curso,
            media_final=media,
            situacao="APROVADO"
        )

        nova_classe = str(classe_atual + 1)

        nova_turma, _ = Turma.objects.get_or_create(
            classe=nova_classe,
            identificador=turma_atual.identificador,
            turno=turma_atual.turno,
            escola=escola,
            ano_letivo=novo_ano,
            curso=turma_atual.curso,
            defaults={"professor": turma_atual.professor}
        )

        aluno.classe = nova_classe
        aluno.turma = nova_turma
        aluno.ano_letivo = novo_ano
        aluno.aprovado = True
        aluno.precisa_confirmacao = True
        aluno.matricula_confirmada = False
        aluno.numero_na_turma = None
        aluno.save()

        promovidos += 1

    # ======================================
    # PDF FINAL (DESIGN PROFISSIONAL)
    # ======================================

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # ================= HEADER =================
    elements.append(Paragraph(
        f"<font size=18><b>{escola.nome}</b></font>",
        styles["Title"]
    ))

    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"<font size=12 color='#666666'>Relatório Oficial de Encerramento do Ano Letivo</font>",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 12))

    # ================= CAIXA DO ANO =================
    elements.append(Paragraph(
        f"<font size=14><b>Ano Letivo: {ano_letivo.nome}</b></font>",
        styles["Normal"]
    ))

    elements.append(Paragraph(
        f"<font size=11 color='#444444'>Novo Ano Criado: {novo_nome}</font>",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 15))

    # ================= RESUMO ESTILO DASHBOARD =================
    data = [
        ["Indicador", "Quantidade"],
        ["Promovidos", str(promovidos)],
        ["Reprovados", str(reprovados)],
        ["Finalistas", str(finalistas)],
    ]

    table = Table(data, colWidths=[300, 200])

    table.setStyle(TableStyle([
        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),

        # BODY
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 11),

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),

        # PADDING
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 20))

    # ================= DATA =================
    elements.append(Paragraph(
        f"<font size=10 color='#6b7280'>Data de emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}</font>",
        styles["Normal"]
    ))

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    from django.http import HttpResponse

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_promocao.pdf"'
    response.write(pdf)

    return response




from django.http import HttpResponse

@login_required
def download_pdf_encerramento(request):

    pdf = request.session.get("pdf_encerramento")

    if not pdf:
        return redirect("dashboard")

    response = HttpResponse(
        pdf.encode("latin1"),
        content_type="application/pdf"
    )

    response["Content-Disposition"] = 'attachment; filename="encerramento.pdf"'

    del request.session["pdf_encerramento"]

    return response




@login_required
def horarios(request):

    if getattr(request.user, "role", None) != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    escola = request.user.escola

    turmas = Turma.objects.filter(
        escola=escola
    ).order_by("classe", "identificador")

    return render(request, "horarios.html", {
        "turmas": turmas
    })




from collections import defaultdict

@login_required
def horarios_turma(request):

    # Apenas diretor
    if getattr(request.user, "role", None) != "DIRETOR_PEDAGOGICO":
        return redirect("dashboard")

    escola = request.user.escola

    # Turmas da escola com curso
    turmas = Turma.objects.select_related("curso").filter(
        escola=escola
    ).order_by("classe", "identificador")

    turma_id = request.GET.get("turma")

    horario = None
    aulas = None
    turma_selecionada = None
    disciplinas = None

    # grade estilo ERP
    grade = defaultdict(dict)

    if turma_id:

        turma_selecionada = get_object_or_404(
            Turma.objects.select_related("curso"),
            id=turma_id,
            escola=escola
        )

        # Criar ou buscar horário
        horario, created = HorarioTurma.objects.get_or_create(
            turma=turma_selecionada,
            escola=escola,
            turno=turma_selecionada.turno
        )

        # Buscar aulas
        aulas = AulaHorario.objects.filter(
            horario=horario
        ).select_related(
            "disciplina",
            "horario__turma__curso"
        ).order_by("hora_inicio")

        # Montar grade tipo calendário
        for aula in aulas:
            hora = aula.hora_inicio.strftime("%H:%M")
            grade[hora][aula.dia] = aula

        # Disciplinas disponíveis
        disciplinas = Disciplina.objects.filter(
            turma=turma_selecionada,
            escola=escola
        ).order_by("nome")

    context = {
        "turmas": turmas,
        "horario": horario,
        "aulas": aulas,
        "grade": dict(grade),
        "turma_selecionada": turma_selecionada,
        "disciplinas": disciplinas,
        "dias_semana": [
            ("SEG", "Segunda"),
            ("TER", "Terça"),
            ("QUA", "Quarta"),
            ("QUI", "Quinta"),
            ("SEX", "Sexta"),
        ]
    }

    return render(request, "horarios_turma.html", context)



from datetime import datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

@login_required
def adicionar_aula(request, horario_id):

    # =========================
    # PERMISSÃO
    # =========================
    if getattr(request.user, "role", None) != "DIRETOR_PEDAGOGICO":
        messages.error(request, "Sem permissão para esta ação.")
        return redirect("dashboard")

    escola = request.user.escola

    horario = get_object_or_404(
        HorarioTurma,
        id=horario_id,
        escola=escola
    )

    # =========================
    # POST
    # =========================
    if request.method == "POST":

        dia = request.POST.get("dia")
        hora_inicio = request.POST.get("hora_inicio")
        hora_fim = request.POST.get("hora_fim")
        tipo = request.POST.get("tipo")
        disciplina_id = request.POST.get("disciplina")
        toda_semana = request.POST.get("toda_semana") == "on"

        # =========================
        # VALIDAÇÃO DE HORAS
        # =========================
        try:
            inicio = datetime.strptime(hora_inicio, "%H:%M").time()
            fim = datetime.strptime(hora_fim, "%H:%M").time()
        except (ValueError, TypeError):
            messages.error(request, "Formato de hora inválido.")
            return redirect(f"/horarios/?turma={horario.turma.id}")

        if inicio >= fim:
            messages.error(request, "A hora final deve ser maior que a inicial.")
            return redirect(f"/horarios/?turma={horario.turma.id}")

        # =========================
        # DISCIPLINA (CASO AULA)
        # =========================
        disciplina = None

        if tipo == "AULA":
            if not disciplina_id:
                messages.error(request, "Selecione uma disciplina.")
                return redirect(f"/horarios/?turma={horario.turma.id}")

            disciplina = get_object_or_404(
                Disciplina,
                id=disciplina_id,
                escola=escola
            )

        # =========================
        # DIAS ÚTEIS
        # =========================
        DIAS_UTEIS = [
            d for d, _ in AulaHorario.DIAS_SEMANA
            if d != "SAB"
        ]

        dias_uso = DIAS_UTEIS if toda_semana else [dia]

        # =========================
        # CRIAÇÃO COM VERIFICAÇÃO DE CONFLITO
        # =========================
        criadas = 0
        ignoradas = 0

        for d in dias_uso:

            conflito = AulaHorario.objects.filter(
                horario=horario,
                dia=d
            ).filter(
                Q(hora_inicio__lt=fim) &
                Q(hora_fim__gt=inicio)
            ).exists()

            if conflito:
                ignoradas += 1
                continue

            AulaHorario.objects.create(
                horario=horario,
                dia=d,
                hora_inicio=inicio,
                hora_fim=fim,
                tipo=tipo,
                disciplina=disciplina
            )

            criadas += 1

        # =========================
        # FEEDBACK INTELIGENTE
        # =========================
        if criadas > 0:
            messages.success(
                request,
                f"{criadas} aula(s) adicionada(s) com sucesso!"
            )

        if ignoradas > 0:
            messages.warning(
                request,
                f"{ignoradas} conflito(s) ignorado(s) por sobreposição de horário."
            )

        return redirect(f"/horarios/?turma={horario.turma.id}")

    return redirect("horarios")


@login_required
def ativar_ano(request, ano_id):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    ano = get_object_or_404(
        AnoLetivo,
        id=ano_id,
        escola=request.user.escola
    )

    if request.method == "POST":
        ano.ativo = True
        ano.save()

        messages.success(request, "Ano letivo ativado com sucesso!")
        return redirect("listar_anos")

    return render(request, "ativar_ano.html", {"ano": ano})












from django.utils import timezone


@login_required
def caixa_diario(request):

    hoje = timezone.now().date()

    entradas = MovimentoCaixa.objects.filter(
        escola=request.user.escola,
        tipo="ENTRADA",
        data__date=hoje
    )

    saidas = MovimentoCaixa.objects.filter(
        escola=request.user.escola,
        tipo="SAIDA",
        data__date=hoje
    )

    total_entradas = sum(e.valor for e in entradas)
    total_saidas = sum(s.valor for s in saidas)

    saldo = total_entradas - total_saidas

    context = {
        "entradas": entradas,
        "saidas": saidas,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo": saldo
    }

    return render(request, "caixa_diario.html", context)



from decimal import Decimal
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone




@login_required
def recibo_pagamento(request):

    # IDs guardados na sessão
    pagamentos_ids = request.session.get("recibos_ids", [])

    # Se não houver pagamentos
    if not pagamentos_ids:
        messages.error(request, "Nenhum pagamento encontrado.")
        return redirect("registrar_pagamento")

    # Buscar pagamentos
    pagamentos = (
        Pagamento.objects
        .select_related(
            "aluno",
            "aluno__usuario",
            "aluno__turma",
            "escola",
            "mensalidade"
        )
        .filter(id__in=pagamentos_ids)
        .order_by("id")
    )

    # Validar existência
    if not pagamentos.exists():
        messages.error(request, "Pagamentos não encontrados.")
        return redirect("registrar_pagamento")

    # Referência principal
    pagamento_ref = pagamentos.first()

    aluno = pagamento_ref.aluno
    escola = pagamento_ref.escola
    turma = getattr(aluno, "turma", None)

    pagamentos_detalhados = []

    total_pago = Decimal("0.00")

    # Processar pagamentos
    for p in pagamentos:

        # Tipo do pagamento
        tipo = "Mensalidade"

        if not p.mensalidade:
            tipo = "Pagamento"

        pagamentos_detalhados.append({
            "tipo": tipo,
            "mes": p.mensalidade.mes if p.mensalidade else None,
            "ano_letivo": p.mensalidade.ano_letivo if p.mensalidade else None,
            "valor": p.valor_pago,
        })

        total_pago += p.valor_pago

    # Número do recibo
    numero_recibo = f"REC-{timezone.now().year}-{random.randint(10000, 99999)}"

    # Contexto
    context = {
        "pagamentos": pagamentos_detalhados,
        "aluno": aluno,
        "escola": escola,
        "turma": turma,
        "total_pago": total_pago,
        "data_emissao": timezone.localtime(),
        "numero_recibo": numero_recibo,
    }

    # Limpar sessão após gerar recibo
    request.session.pop("recibos_ids", None)

    # Renderizar template
    return render(
        request,
        "financeiro/recibo.html",
        context
    )




# ==========================================================
# CONFIGURAÇÃO FINANCEIRA
# ==========================================================

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
@login_required
def configuracao_financeira(request):

    # ==========================================================
    # PERMISSÃO
    # ==========================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

    config, created = ConfiguracaoFinanceira.objects.get_or_create(
        escola=escola
    )

    # ==========================================================
    # FUNÇÃO AUXILIAR
    # ==========================================================

    def converter_decimal(valor):

        if not valor:
            return Decimal("0.00")

        valor = valor.replace(",", ".")

        return Decimal(valor)

    # ==========================================================
    # SALVAR CONFIGURAÇÃO
    # ==========================================================

    if request.method == "POST":

        try:

            with transaction.atomic():

                # -------------------------------
                # MENSALIDADES POR CLASSE
                # -------------------------------



                valor_mensalidade_4 = converter_decimal(
                    request.POST.get("valor_mensalidade_4")
                )

                valor_mensalidade_5 = converter_decimal(
                    request.POST.get("valor_mensalidade_5")
                )

                valor_mensalidade_6 = converter_decimal(
                    request.POST.get("valor_mensalidade_6")
                )

                valor_mensalidade_7 = converter_decimal(
                    request.POST.get("valor_mensalidade_7")
                )

                valor_mensalidade_8 = converter_decimal(
                    request.POST.get("valor_mensalidade_8")
                )

                valor_mensalidade_9 = converter_decimal(
                    request.POST.get("valor_mensalidade_9")
                )

                valor_mensalidade_10 = converter_decimal(
                    request.POST.get("valor_mensalidade_10")
                )

                valor_mensalidade_11 = converter_decimal(
                    request.POST.get("valor_mensalidade_11")
                )

                valor_mensalidade_12 = converter_decimal(
                    request.POST.get("valor_mensalidade_12")
                )

                valor_mensalidade_13 = converter_decimal(
                    request.POST.get("valor_mensalidade_13")
                )

                # -------------------------------
                # OUTROS VALORES
                # -------------------------------

                valor_matricula = converter_decimal(
                    request.POST.get("valor_matricula")
                )

                valor_declaracao = converter_decimal(
                    request.POST.get("valor_declaracao")
                )

                valor_exame = converter_decimal(
                    request.POST.get("valor_exame")
                )

                valor_multa_mensalidade = converter_decimal(
                    request.POST.get("valor_multa_mensalidade")
                )

                valor_multa_matricula = converter_decimal(
                    request.POST.get("valor_multa_matricula")
                )

        except (InvalidOperation, TypeError):

            messages.error(
                request,
                "Algum valor informado é inválido."
            )

            return redirect("configuracao_financeira")

        # ==========================================================
        # VALIDAÇÕES
        # ==========================================================

        campos = [


            valor_mensalidade_4,
            valor_mensalidade_5,
            valor_mensalidade_6,
            valor_mensalidade_7,
            valor_mensalidade_8,
            valor_mensalidade_9,
            valor_mensalidade_10,
            valor_mensalidade_11,
            valor_mensalidade_12,
            valor_mensalidade_13,

            valor_matricula,
            valor_declaracao,
            valor_exame,
            valor_multa_mensalidade,
            valor_multa_matricula,

        ]

        if any(valor < 0 for valor in campos):

            messages.error(
                request,
                "Nenhum valor pode ser negativo."
            )

            return redirect("configuracao_financeira")

        # ==========================================================
        # SALVAR
        # ==========================================================


        config.valor_mensalidade_4 = valor_mensalidade_4
        config.valor_mensalidade_5 = valor_mensalidade_5
        config.valor_mensalidade_6 = valor_mensalidade_6
        config.valor_mensalidade_7 = valor_mensalidade_7
        config.valor_mensalidade_8 = valor_mensalidade_8
        config.valor_mensalidade_9 = valor_mensalidade_9
        config.valor_mensalidade_10 = valor_mensalidade_10
        config.valor_mensalidade_11 = valor_mensalidade_11
        config.valor_mensalidade_12 = valor_mensalidade_12
        config.valor_mensalidade_13 = valor_mensalidade_13

        config.valor_matricula = valor_matricula
        config.valor_declaracao = valor_declaracao
        config.valor_exame = valor_exame
        config.valor_multa_mensalidade = valor_multa_mensalidade
        config.valor_multa_matricula = valor_multa_matricula

        config.save()

        # ==========================================================
        # ATUALIZAR MENSALIDADES SEM VALOR
        # ==========================================================

        mensalidades_sem_valor = Mensalidade.objects.filter(
            aluno__escola=escola,
            valor__lte=0
        ).select_related("aluno__turma")

        mensalidades_atualizadas = 0

        for mensalidade in mensalidades_sem_valor:

            classe = mensalidade.aluno.turma.classe

            mensalidade.valor = config.obter_valor_mensalidade(classe)

            mensalidade.save(update_fields=["valor"])

            mensalidade.atualizar_status()

            mensalidades_atualizadas += 1

        # ==========================================================
        # SUCESSO
        # ==========================================================

        messages.success(
            request,
            f"""
Configuração financeira salva com sucesso.

Mensalidades por classe atualizadas.
Valor da matrícula: {valor_matricula} Kz
Valor da declaração: {valor_declaracao} Kz
Valor do exame: {valor_exame} Kz

Mensalidades corrigidas: {mensalidades_atualizadas}
"""
        )

        return redirect("configuracao_financeira")

    # ==========================================================
    # TEMPLATE
    # ==========================================================

    context = {
        "config": config
    }

    return render(
        request,
        "configuracao_financeira.html",
        context
    )



@login_required
def editar_aluno(request, aluno_id):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    escola = request.user.escola

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola
    )

    turmas = Turma.objects.filter(escola=escola)

    if request.method == "POST":

        aluno.usuario.first_name = request.POST.get("nome")
        aluno.usuario.email = request.POST.get("email")
        aluno.usuario.save()

        aluno.numero_bi = request.POST.get("numero_bi")
        aluno.data_nascimento = request.POST.get("data_nascimento")
        aluno.sexo = request.POST.get("sexo")

        turma_id = request.POST.get("turma")

        if turma_id:
            turma = Turma.objects.get(id=turma_id)
            aluno.turma = turma
            aluno.classe = turma.classe

        aluno.save()

        messages.success(request, "Aluno atualizado com sucesso.")
        return redirect("alunos")

    return render(request, "editar_aluno.html", {
        "aluno": aluno,
        "turmas": turmas
    })


@login_required
def eliminar_aluno(request, aluno_id):

    if request.user.role != "DIRETOR":
        return redirect("dashboard")

    escola = request.user.escola

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola
    )

    aluno.delete()

    messages.success(request, "Aluno eliminado com sucesso.")

    return redirect("alunos")


def relatorio_mensalidades(request):

    turmas = Turma.objects.all()
    meses = [
        "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
        "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
    ]

    turma_id = request.GET.get("turma")
    mes = request.GET.get("mes")

    mensalidades = []

    if turma_id and mes:
        mensalidades = Mensalidade.objects.filter(
            aluno__turma_id=turma_id,
            mes=mes
        ).select_related("aluno")

    context = {
        "turmas": turmas,
        "meses": meses,
        "mensalidades": mensalidades,
        "turma_id": turma_id,
        "mes": mes
    }

    return render(request, "relatorio_mensalidades.html", context)






from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

def exportar_estado_turma_pdf(request):
    #  Captura parâmetros
    turma_id = request.GET.get("turma")
    mes = request.GET.get("mes")

    #  Busca dados
    turma = Turma.objects.get(id=turma_id)
    mensalidades = Mensalidade.objects.filter(
        aluno__turma_id=turma_id,
        mes=mes
    ).select_related("aluno")

    #  Cria resposta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="estado_turma_{turma.identificador}_{mes}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    #  Cabeçalho
    pdf.setFillColor(colors.HexColor("#2E86C1"))  # Azul corporativo
    pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 50, "Relatório de Estado da Turma")

    #  Logo (opcional: coloque o caminho correto da imagem)
    # pdf.drawImage("media/logo.png", 50, height - 70, width=50, preserveAspectRatio=True, mask='auto')

    #  Informações da turma
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    y = height - 110
    pdf.drawString(50, y, f"Turma: {turma.identificador}")
    pdf.drawString(250, y, f"Mês: {mes}")
    pdf.drawString(400, y, f"Total Alunos: {mensalidades.count()}")
    y -= 30

    #  Tabela de dados
    data = [["Aluno", "Processo", "Status"]]
    total_pagos = 0
    total_atrasados = 0

    for m in mensalidades:
        status = "PAGA" if m.status == "PAGA" else "ATRASADA"
        data.append([m.aluno.usuario.get_full_name(), str(m.aluno.numero_processo), status])

        if status == "PAGA":
            total_pagos += 1
        else:
            total_atrasados += 1

    #  Adiciona totalizadores
    data.append(["", "", ""])
    data.append(["Total Pagos", total_pagos, ""])
    data.append(["Total Atrasados", total_atrasados, ""])

    #  Estilo da tabela
    table = Table(data, colWidths=[8*cm, 4*cm, 4*cm])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('ROWBACKGROUNDS', (1,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
         ])
    table.setStyle(style)

    #  Desenha tabela
    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, 50, y - (len(data) * 20))

    # Rodapé
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(colors.grey)
    pdf.drawString(50, 30, "Sistema Escolar SaaS - Todos os direitos reservados")
    pdf.drawRightString(width - 50, 30, f"Pág. 1")

    pdf.showPage()
    pdf.save()

    return response



from academic.models import Mensalidade


@login_required
def situacao_financeira(request):

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    aluno = Aluno.objects.filter(usuario=request.user).first()

    if not aluno:
        return redirect("dashboard")

    # Buscar mensalidades
    mensalidades = Mensalidade.objects.filter(
        aluno=aluno
    ).order_by("vencimento")

    # Atualizar status automaticamente
    for m in mensalidades:
        m.atualizar_status()

    # Buscar dívidas
    dividas = mensalidades.filter(
        status__in=["PENDENTE", "ATRASADA"]
    )

    tem_divida = dividas.exists()

    total_divida = dividas.aggregate(
        total=Sum("valor")
    )["total"] or 0

    total_pago = mensalidades.filter(
        status="PAGA"
    ).aggregate(
        total=Sum("valor")
    )["total"] or 0

    context = {
        "aluno": aluno,
        "dividas": dividas,
        "mensalidades": mensalidades,
        "tem_divida": tem_divida,
        "total_divida": total_divida,
        "total_pago": total_pago,
    }

    return render(
        request,
        "situacao_financeira.html",
        context
    )





from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

@login_required
def cursos(request):

    escola = get_escola(request)

    if not escola:
        return redirect("dashboard")

    user = request.user

    # =====================================================
    # BASE TEMPLATE DINÂMICO
    # =====================================================
    if user.role == "DIRETOR_PEDAGOGICO":
        base_template = "base_diretor_pedagogico.html"
    elif user.role == "DIRETOR":
        base_template = "base.html"
    else:
        return redirect("dashboard")

    # =====================================================
    # LISTA DE CURSOS
    # =====================================================
    cursos = Curso.objects.filter(
        escola=escola
    ).order_by("nome")

    # =====================================================
    # CRIAÇÃO DE CURSO (APENAS DIRETOR PEDAGÓGICO)
    # =====================================================
    if request.method == "POST":

        if user.role != "DIRETOR_PEDAGOGICO":
            messages.error(request, "Sem permissão para criar cursos.")
            return redirect("cursos")

        nome = request.POST.get("nome", "").strip()
        descricao = request.POST.get("descricao", "").strip()

        if not nome:
            messages.error(request, "Informe o nome do curso.")
            return redirect("cursos")

        if Curso.objects.filter(
            escola=escola,
            nome__iexact=nome
        ).exists():

            messages.warning(
                request,
                "Já existe um curso com este nome."
            )
            return redirect("cursos")

        Curso.objects.create(
            escola=escola,
            nome=nome,
            descricao=descricao
        )

        messages.success(
            request,
            "Curso criado com sucesso."
        )

        return redirect("cursos")

    # =====================================================
    # CONTEXTO
    # =====================================================
    context = {
        "cursos": cursos,
        "total_cursos": cursos.count(),
        "base_template": base_template,
    }

    return render(
        request,
        "cursos.html",
        context
    )


from django.contrib import messages
from django.shortcuts import get_object_or_404

@login_required
def editar_curso(request, curso_id):

    escola = request.user.escola

    curso = get_object_or_404(
        Curso,
        id=curso_id,
        escola=escola
    )

    if request.method == "POST":

        nome = request.POST.get("nome", "").strip()
        descricao = request.POST.get("descricao", "").strip()

        if not nome:

            messages.error(
                request,
                "Informe o nome do curso."
            )

            return redirect("cursos")

        existe = Curso.objects.filter(
            escola=escola,
            nome__iexact=nome
        ).exclude(
            id=curso.id
        ).exists()

        if existe:

            messages.warning(
                request,
                "Já existe outro curso com este nome."
            )

            return redirect("cursos")

        curso.nome = nome
        curso.descricao = descricao
        curso.save()

        messages.success(
            request,
            "Curso atualizado com sucesso."
        )

        return redirect("cursos")

    return redirect("cursos")


@login_required
def eliminar_curso(request, curso_id):

    escola = request.user.escola

    curso = get_object_or_404(
        Curso,
        id=curso_id,
        escola=escola
    )

    possui_turmas = Turma.objects.filter(
        curso=curso
    ).exists()

    if possui_turmas:

        messages.error(
            request,
            "Não é possível eliminar este curso porque existem turmas associadas."
        )

        return redirect("cursos")

    curso.delete()

    messages.success(
        request,
        "Curso eliminado com sucesso."
    )

    return redirect("cursos")


# ==========================================================
# GERAR RECIBO
# ==========================================================

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render, redirect

@login_required
def gerar_recibo(request, pagamento_id):

    # ==========================================================
    # PERMISSÃO
    # ==========================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # ==========================================================
    # PAGAMENTO
    # ==========================================================

    pagamento = get_object_or_404(

        Pagamento.objects.select_related(
            "aluno",
            "aluno__usuario",
            "aluno__turma",
            "aluno__turma__curso",
            "mensalidade",
            "ano_letivo",
            "recebido_por",
            "escola"
        ),

        id=pagamento_id,
        escola=escola

    )

    # ==========================================================
    # DADOS
    # ==========================================================

    aluno = pagamento.aluno

    turma = getattr(aluno, "turma", None)

    curso = getattr(turma, "curso", None) if turma else None

    mensalidade = pagamento.mensalidade

    # ==========================================================
    # STATUS
    # ==========================================================

    status = "CONFIRMADO"

    if mensalidade:

        mensalidade.atualizar_status()

        status = mensalidade.status

    # ==========================================================
    # TOTAL PAGO
    # ==========================================================

    total_pago = pagamento.valor_pago or Decimal("0.00")

    # ==========================================================
    # DESCRIÇÃO
    # ==========================================================

    descricao = pagamento.get_tipo_display()

    if pagamento.tipo == "MENSALIDADE" and mensalidade:

        descricao = (
            f"Pagamento da Mensalidade "
            f"de {mensalidade.mes}"
        )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {

        "pagamento": pagamento,

        "mensalidade": mensalidade,

        "aluno": aluno,

        "turma": turma,

        "curso": curso,

        "escola": escola,

        "descricao": descricao,

        "total_pago": total_pago,

        "status": status,

    }

    return render(
        request,
        "gerar_recibo.html",
        context
    )


@login_required
def alterar_senha(request):

    if request.method == "POST":

        senha1 = request.POST.get("senha1")
        senha2 = request.POST.get("senha2")

        if senha1 != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect("alterar_senha")

        if len(senha1) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return redirect("alterar_senha")

        user = request.user
        user.set_password(senha1)
        user.save()

        messages.success(request, "Senha alterada com sucesso. Faça login novamente.")
        return redirect("login")

    return render(request, "alterar_senha.html")

@login_required
def alterar_senha_secretaria(request):

    if request.method == "POST":

        senha1 = request.POST.get("senha1")
        senha2 = request.POST.get("senha2")

        if senha1 != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect("alterar_senha")

        if len(senha1) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return redirect("alterar_senha")

        user = request.user
        user.set_password(senha1)
        user.save()

        messages.success(request, "Senha alterada com sucesso. Faça login novamente.")
        return redirect("login")
    return render(request, "alterar_senha_secretaria.html")


@login_required
def alterar_senha_financeiro(request):

    if request.method == "POST":

        senha1 = request.POST.get("senha1")
        senha2 = request.POST.get("senha2")

        if senha1 != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect("alterar_senha")

        if len(senha1) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return redirect("alterar_senha")

        user = request.user
        user.set_password(senha1)
        user.save()

        messages.success(request, "Senha alterada com sucesso. Faça login novamente.")
        return redirect("login")
    return render(request, "alterar_senha_financeiro.html")

@login_required
def alterar_senha_professor(request):

    if request.method == "POST":

        senha1 = request.POST.get("senha1")
        senha2 = request.POST.get("senha2")

        if senha1 != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect("alterar_senha")

        if len(senha1) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return redirect("alterar_senha")

        user = request.user
        user.set_password(senha1)
        user.save()

        messages.success(request, "Senha alterada com sucesso. Faça login novamente.")
        return redirect("login")

    return render(request, "alterar_senha_professor.html")


@login_required
def alterar_senha_aluno(request):

    if request.method == "POST":

        senha1 = request.POST.get("senha1")
        senha2 = request.POST.get("senha2")

        if senha1 != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect("alterar_senha")

        if len(senha1) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return redirect("alterar_senha")

        user = request.user
        user.set_password(senha1)
        user.save()

        messages.success(request, "Senha alterada com sucesso. Faça login novamente.")
        return redirect("login")

    return render(request, "alterar_senha_aluno.html")


#=============================================================
#  GERENCIAMENTO SUPERADMIN
#=============================================================

def gerenciar_planos(request):
    planos = Plano.objects.all()
    return render(request, 'planos.html', {'planos': planos})

from django.shortcuts import render
from academic.models import PagamentoPlano


def gerenciar_pagamentos(request):
    pagamentos = PagamentoPlano.objects.select_related('escola', 'plano').all().order_by('-criado_em')
    return render(request, 'pagamentos_escola.html', {'pagamentos': pagamentos})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from academic.models import PagamentoPlano


def editar_pagamento(request, pagamento_id):

    pagamento = get_object_or_404(PagamentoPlano, id=pagamento_id)

    if request.method == "POST":

        pagamento.mes_referencia = request.POST.get("mes_referencia")
        pagamento.valor = request.POST.get("valor")
        pagamento.data_vencimento = request.POST.get("data_vencimento")
        pagamento.data_pagamento = request.POST.get("data_pagamento") or None
        pagamento.status = request.POST.get("status")

        pagamento.save()

        messages.success(request, "Pagamento atualizado com sucesso!")
        return redirect("gerenciar_pagamentos")

    return render(request, "editar_pagamento.html", {
        "pagamento": pagamento
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


def deletar_pagamento(request, id):


    pagamento = get_object_or_404(
        PagamentoPlano,
        id=id
    )



    if request.method == "POST":


        pagamento.delete()



        messages.success(
            request,
            "Pagamento eliminado com sucesso."
        )



        return redirect(
            "pagamentos_escolas"
        )




    return render(
        request,
        "confirmar_delete_pagamento.html",
        {
            "pagamento": pagamento
        }
    )

from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError


# ==============================
# ANO LETIVO AUTOMÁTICO
# ==============================
def get_ano_letivo_atual():
    hoje = date.today()
    return f"{hoje.year}/{hoje.year + 1}"


from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect
import logging


logger = logging.getLogger(__name__)




@staff_member_required
@transaction.atomic
def configuracoes(request):
    """
    Painel de Configurações Globais EdusCel.

    Regras:
    - Apenas Staff/SuperAdmin
    - Configuração única (Singleton)
    - Controle central do SaaS
    """



    # =====================================================
    # CONFIGURAÇÃO GLOBAL SINGLETON
    # =====================================================

    config, created = Configuracao.objects.get_or_create(
        pk=1
    )



    # =====================================================
    # GARANTIR ANO LETIVO PADRÃO
    # =====================================================

    if not config.ano_letivo_padrao:


        config.ano_letivo_padrao = (
            get_ano_letivo_atual()
        )


        config.save(
            update_fields=[
                "ano_letivo_padrao"
            ]
        )





    # =====================================================
    # PROCESSAMENTO DO FORMULÁRIO
    # =====================================================

    if request.method == "POST":


        form = ConfiguracaoForm(

            request.POST,

            request.FILES,

            instance=config

        )



        if form.is_valid():


            try:


                with transaction.atomic():



                    # =====================================
                    # ESTADO ANTERIOR
                    # (Preparação para auditoria)
                    # =====================================

                    config_anterior = (
                        Configuracao.objects
                        .select_for_update()
                        .get(pk=1)
                    )





                    config = form.save(
                        commit=False
                    )





                    # =====================================
                    # GARANTIA DE SEGURANÇA
                    # =====================================

                    if not config.ano_letivo_padrao:

                        config.ano_letivo_padrao = (
                            get_ano_letivo_atual()
                        )





                    # =====================================
                    # ATUALIZAÇÃO
                    # =====================================

                    config.save()


                    form.save_m2m()





                    # =====================================
                    # FUTURO:
                    # AUDITORIA DO SISTEMA
                    # =====================================

                    """
                    AuditLog.objects.create(
                        usuario=request.user,
                        modulo="CONFIGURACAO",
                        acao="ALTERACAO",
                        descricao=
                        "Configurações globais atualizadas"
                    )
                    """





                    messages.success(

                        request,

                        "Configurações globais atualizadas com sucesso."

                    )



                    return redirect(
                        "configuracoes"
                    )





            except ValidationError as error:


                logger.warning(
                    f"Erro validação configuração: {error}"
                )


                messages.error(

                    request,

                    f"Erro de validação: {error}"

                )





            except Exception as error:


                logger.exception(
                    "Erro ao atualizar configurações globais"
                )


                messages.error(

                    request,

                    "Ocorreu um erro inesperado ao salvar as configurações."

                )






        else:


            messages.warning(

                request,

                "Existem campos inválidos. Verifique o formulário."

            )





    else:


        form = ConfiguracaoForm(
            instance=config
        )





    # =====================================================
    # CONTEXTO GLOBAL
    # =====================================================

    context = {


        "form": form,


        "config": config,


        "created": created,



        # STATUS GLOBAL

        "modo_manutencao":
            config.modo_manutencao,



        "nome_sistema":
            config.nome_sistema,



        # ANO LETIVO

        "ano_letivo_atual":
            (
                config.ano_letivo_padrao
                or
                get_ano_letivo_atual()
            ),



        # INFORMAÇÕES PARA DASHBOARD FUTURO

        "sistema_ativo":
            not config.modo_manutencao,

    }





    return render(

        request,

        "configuracoes.html",

        context

    )



from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from academic.models import Plano


@staff_member_required
def editar_plano(request, plano_id):

    plano = get_object_or_404(Plano, id=plano_id)

    if request.method == "POST":

        try:
            plano.nome = request.POST.get("nome")

            plano.limite_alunos = int(request.POST.get("limite_alunos") or 0)
            plano.limite_professores = int(request.POST.get("limite_professores") or 0)
            plano.limite_turmas = int(request.POST.get("limite_turmas") or 0)

            plano.valor_mensal = float(request.POST.get("valor_mensal") or 0)

            plano.data_expiracao = request.POST.get("data_expiracao") or None

            plano.ativo = True if request.POST.get("ativo") == "on" else False

            plano.save()

            messages.success(request, "Plano atualizado com sucesso!")
            return redirect("gerenciar_planos")

        except Exception as e:
            messages.error(request, f"Erro ao atualizar plano: {str(e)}")

    return render(request, "editar_plano.html", {"plano": plano})


@login_required
def excluir_plano(request, plano_id):

    plano = get_object_or_404(Plano, id=plano_id)

    plano.delete()

    messages.success(request, "Plano excluído com sucesso!")

    return redirect("planos")


#===========================================================
#   FINANCEIRO
#===========================================================


from decimal import Decimal
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render

from .services import dados_financeiros_da_secretaria


@login_required
def dashboard_financeiro(request):
    """
    Dashboard do Financeiro.
    Apresenta indicadores financeiros, gráfico mensal e últimos movimentos.
    """

    if getattr(request.user, "role", None) != "FINANCEIRO":
        return redirect("dashboard")

    escola = getattr(request.user, "escola", None)

    if escola is None:
        return redirect("dashboard")

    # =====================================================
    # CONSULTAS
    # =====================================================

    pagamentos = (
        Pagamento.objects
        .filter(aluno__escola=escola)
    )

    despesas = (
        Despesa.objects
        .filter(escola=escola)
    )

    # =====================================================
    # TOTAIS
    # =====================================================

    total_entradas = (
        pagamentos.aggregate(total=Sum("valor_pago"))["total"]
        or Decimal("0.00")
    )

    total_saidas = (
        despesas.aggregate(total=Sum("valor"))["total"]
        or Decimal("0.00")
    )

    saldo = total_entradas - total_saidas

    # =====================================================
    # ÚLTIMOS MOVIMENTOS
    # =====================================================

    ultimos_pagamentos = pagamentos.order_by("-data_pagamento")[:10]
    ultimas_despesas = despesas.order_by("-data")[:10]

    # =====================================================
    # RELATÓRIO MENSAL
    # =====================================================

    pagamentos_mensais = (
        pagamentos
        .annotate(mes=TruncMonth("data_pagamento"))
        .values("mes")
        .annotate(total=Sum("valor_pago"))
        .order_by("mes")
    )

    despesas_mensais = (
        despesas
        .annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(total=Sum("valor"))
        .order_by("mes")
    )

    dados_por_mes = {}

    for item in pagamentos_mensais:
        chave = item["mes"]
        dados_por_mes.setdefault(
            chave,
            {
                "entradas": 0,
                "despesas": 0,
            },
        )
        dados_por_mes[chave]["entradas"] = float(item["total"])

    for item in despesas_mensais:
        chave = item["mes"]
        dados_por_mes.setdefault(
            chave,
            {
                "entradas": 0,
                "despesas": 0,
            },
        )
        dados_por_mes[chave]["despesas"] = float(item["total"])

    meses = []
    entradas_chart = []
    despesas_chart = []

    for mes in sorted(dados_por_mes.keys()):
        meses.append(mes.strftime("%b"))
        entradas_chart.append(dados_por_mes[mes]["entradas"])
        despesas_chart.append(dados_por_mes[mes]["despesas"])

    # =====================================================
    # DADOS DA SECRETARIA
    # =====================================================

    dados_secretaria = dados_financeiros_da_secretaria(escola)

    # =====================================================
    # CONTEXTO
    # =====================================================

    context = {
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo": saldo,

        "pagamentos": ultimos_pagamentos,
        "despesas": ultimas_despesas,

        "meses": json.dumps(meses),
        "entradas_mensais": json.dumps(entradas_chart),
        "despesas_mensais": json.dumps(despesas_chart),

        **dados_secretaria,
    }

    return render(
        request,
        "dashboard_financeiro.html",
        context,
    )


@login_required
def adicionar_despesa(request):

    if request.user.role not in ["FINANCEIRO", "DIRETOR"]:
        return redirect("dashboard")

    escola = request.user.escola

    if request.method == "POST":

        descricao = request.POST.get("descricao")
        valor = request.POST.get("valor")

        Despesa.objects.create(
            escola=escola,
            descricao=descricao,
            valor=valor,
            criado_por=request.user
        )

        messages.success(request, "Despesa registrada com sucesso.")
        return redirect("dashboard_financeiro")

    return render(request, "adicionar_despesa.html")



@login_required
def toggle_trimestre(request, trimestre_id):
    if request.user.role != "DIRETOR":
        return redirect('dashboard')

    trimestre = get_object_or_404(Trimestre, id=trimestre_id, escola=request.user.escola)
    trimestre.fechado = not trimestre.fechado
    trimestre.save()

    # Redireciona de volta para o dashboard
    return redirect('painel_diretor')




import csv

from openpyxl import Workbook
from django.http import HttpResponse


@login_required
def entradas_financeiro(request):
    # ================== PERMISSÕES ==================
    if request.user.role not in ["FINANCEIRO", "DIRETOR"]:
        return redirect("dashboard")

    escola = request.user.escola

    # ================== QUERY INICIAL ==================
    pagamentos = Pagamento.objects.filter(aluno__escola=escola).order_by("-data_pagamento")

    # ================== FILTRO POR MÊS E ANO ==================
    mes = request.GET.get("mes")
    ano = request.GET.get("ano")
    if mes and ano:
        try:
            pagamentos = pagamentos.filter(
                data_pagamento__month=int(mes),
                data_pagamento__year=int(ano)
            )
        except ValueError:
            pass  # Ignora valores inválidos

    total_entradas = pagamentos.aggregate(total=Sum("valor_pago"))["total"] or 0

    # ================== EXPORTAÇÃO EXCEL ==================
    if "export_excel" in request.GET:
        wb = Workbook()
        ws = wb.active
        ws.title = "Entradas Financeiras"

        # Cabeçalho
        ws.append(["Aluno", "Descrição", "Valor (Kz)", "Data"])

        # Linhas
        for p in pagamentos:
            desc = p.mensalidade.mes if p.mensalidade else "Pagamento"
            ws.append([
                p.aluno.usuario.get_full_name(),
                desc,
                float(p.valor_pago),
                p.data_pagamento.strftime("%d/%m/%Y")
            ])

        # Preparar resposta
        buffer = BytesIO()
        wb.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=Entradas.xlsx"
        return response

    # ================== LISTA DE MESES ==================
    MESES = [
        ('1','Janeiro'),('2','Fevereiro'),('3','Março'),('4','Abril'),
        ('5','Maio'),('6','Junho'),('7','Julho'),('8','Agosto'),
        ('9','Setembro'),('10','Outubro'),('11','Novembro'),('12','Dezembro')
    ]

    # ================== CONTEXTO PARA TEMPLATE ==================
    context = {
        "pagamentos": pagamentos,
        "total_entradas": total_entradas,
        "mes": mes or "",
        "ano": ano or "",
        "MESES": MESES,
    }

    return render(request, "entradas_financeiro.html", context)






@login_required
def adicionar_entrada(request):

    if request.user.role not in ["FINANCEIRO", "DIRETOR"]:
        return redirect("dashboard")

    escola = request.user.escola

    if request.method == "POST":

        descricao = request.POST.get("descricao")
        valor = request.POST.get("valor")

        Entrada.objects.create(
            escola=escola,
            descricao=descricao,
            valor=valor,
            criado_por=request.user
        )

        messages.success(request, "Entrada registrada com sucesso")
        return redirect("entradas_financeiro")

    return render(request, "adicionar_entrada.html")


@login_required
def lista_despesas(request):

    if getattr(request.user, "role", None) != "FINANCEIRO":
        return redirect("login")

    escola = request.user.escola

    despesas = Despesa.objects.filter(
        escola=escola
    ).order_by("-data")

    total_despesas = despesas.aggregate(
        total=Sum("valor")
    )["total"] or 0

    context = {
        "despesas": despesas,
        "total_despesas": total_despesas
    }

    return render(request, "lista_despesas.html", context)

@login_required
def excluir_despesa(request, id):

    despesa = get_object_or_404(Despesa, id=id)

    if request.user.role != "FINANCEIRO":
        return redirect("dashboard_financeiro")

    despesa.delete()

    messages.success(request, "Despesa removida.")

    return redirect("lista_despesas")


# ==========================================================
# HISTÓRICO ACADÉMICO
# ==========================================================

@login_required
def historico_academico(request):

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    aluno = Aluno.objects.filter(
        usuario=request.user
    ).first()

    if not aluno:
        return redirect("dashboard")

    historicos = HistoricoAcademico.objects.filter(
        aluno=aluno
    ).select_related(
        "ano_letivo",
        "turma"
    )

    context = {
        "aluno": aluno,
        "historicos": historicos
    }

    return render(
        request,
        "historico_academico.html",
        context
    )


# ==========================================================
# BOLETIM PDF HISTÓRICO
# ==========================================================

@login_required
def boletim_historico_pdf(request, historico_id):

    if getattr(request.user, "role", None) != "ALUNO":
        return redirect("dashboard")

    aluno = Aluno.objects.filter(
        usuario=request.user
    ).first()

    historico = get_object_or_404(
        HistoricoAcademico,
        id=historico_id,
        aluno=aluno
    )

    ano_letivo = historico.ano_letivo

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f'attachment; filename="boletim_{ano_letivo.nome}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            f"Boletim Escolar - {ano_letivo.nome}",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 20))

    notas = Nota.objects.filter(
        aluno=aluno,
        ano_letivo=ano_letivo
    ).select_related("disciplina")

    data = [[
        "Disciplina",
        "Trimestre",
        "P1",
        "P2",
        "Média"
    ]]

    for nota in notas:

        data.append([
            nota.disciplina.nome,
            f"{nota.trimestre}º",
            nota.p1,
            nota.p2,
            nota.media
        ])

    tabela = Table(data, repeatRows=1)

    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.grey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))

    elements.append(tabela)

    doc.build(elements)

    return response



# ==========================================================
# HISTÓRICO ACADÊMICO DO PROFESSOR
# ==========================================================

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q

@login_required
def historico_professor(request):

    # ======================================================
    # PERMISSÃO
    # ======================================================

    if getattr(request.user, "role", None) != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    # ======================================================
    # ANO LETIVO ATIVO
    # ======================================================

    ano_ativo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    # ======================================================
    # ANOS PASSADOS
    # ======================================================

    anos_passados = AnoLetivo.objects.filter(
        escola=escola
    ).exclude(
        id=ano_ativo.id if ano_ativo else None
    ).order_by("-id")

    ano_id = request.GET.get("ano")
    turma_id = request.GET.get("turma")

    ano_selecionado = None
    turma_selecionada = None

    turmas = []
    disciplinas_historico = []

    # ======================================================
    # BUSCAR ANO
    # ======================================================

    if ano_id:

        ano_selecionado = AnoLetivo.objects.filter(
            id=ano_id,
            escola=escola
        ).first()

        if ano_selecionado:

            # ==================================================
            # TURMAS DO PROFESSOR NO ANO SELECIONADO
            # ==================================================

            turmas = (
                Turma.objects
                .filter(
                    ano_letivo=ano_selecionado,
                    disciplinas__professor=professor
                )
                .distinct()
                .order_by("classe", "identificador")
            )

    # ======================================================
    # BUSCAR TURMA
    # ======================================================

    if turma_id and ano_selecionado:

        turma_selecionada = Turma.objects.filter(
            id=turma_id,
            ano_letivo=ano_selecionado,
            escola=escola
        ).first()

        if turma_selecionada:

            # ==================================================
            # DISCIPLINAS DO PROFESSOR
            # ==================================================

            disciplinas = Disciplina.objects.filter(
                professor=professor,
                turma=turma_selecionada,
                escola=escola
            ).order_by("nome")

            alunos = (
                Aluno.objects
                .filter(
                    turma=turma_selecionada,
                    ano_letivo=ano_selecionado
                )
                .select_related("usuario")
                .order_by("numero_na_turma")
            )

            # ==================================================
            # LOOP DISCIPLINAS
            # ==================================================

            for disciplina in disciplinas:

                lista_alunos = []

                for aluno in alunos:

                    # ==========================================
                    # NOTAS
                    # ==========================================

                    notas = Nota.objects.filter(
                        aluno=aluno,
                        disciplina=disciplina,
                        ano_letivo=ano_selecionado
                    )

                    nota_t1 = notas.filter(trimestre=1).first()
                    nota_t2 = notas.filter(trimestre=2).first()
                    nota_t3 = notas.filter(trimestre=3).first()

                    media_t1 = (
                        float(nota_t1.media_final)
                        if nota_t1 and nota_t1.media_final is not None
                        else None
                    )

                    media_t2 = (
                        float(nota_t2.media_final)
                        if nota_t2 and nota_t2.media_final is not None
                        else None
                    )

                    media_t3 = (
                        float(nota_t3.media_final)
                        if nota_t3 and nota_t3.media_final is not None
                        else None
                    )

                    # ==========================================
                    # MÉDIA FINAL
                    # ==========================================

                    medias = [
                        m for m in [
                            media_t1,
                            media_t2,
                            media_t3
                        ]
                        if m is not None
                    ]

                    media_final = None
                    status = "-"

                    if medias:

                        media_final = round(
                            sum(medias) / len(medias),
                            1
                        )

                        status = (
                            "APROVADO"
                            if media_final >= 10
                            else "REPROVADO"
                        )

                    # ==========================================
                    # DADOS ALUNO
                    # ==========================================

                    lista_alunos.append({

                        "numero": aluno.numero_na_turma,

                        "nome": (
                            aluno.usuario.get_full_name()
                            or aluno.usuario.username
                        ),

                        "processo": aluno.numero_processo,

                        "t1": media_t1,

                        "t2": media_t2,

                        "t3": media_t3,

                        "media_final": media_final,

                        "status": status,

                    })

                disciplinas_historico.append({

                    "disciplina": disciplina,

                    "alunos": lista_alunos

                })

    # ======================================================
    # CONTEXTO
    # ======================================================

    context = {

        "anos_passados": anos_passados,

        "ano_selecionado": ano_selecionado,

        "turmas": turmas,

        "turma_selecionada": turma_selecionada,

        "disciplinas_historico": disciplinas_historico,

    }

    return render(
        request,
        "historico_professor.html",
        context
    )


# ==========================================================
# CALENDÁRIO ESCOLAR
# ==========================================================

@login_required
def calendario_escolar(request):

    escola = request.user.escola

    eventos = CalendarioEscolar.objects.filter(
        escola=escola
    ).order_by("data_inicio")

    context = {
        "eventos": eventos
    }

    return render(
        request,
        "calendario_escolar.html",
        context
    )


# =====================================================
# CRIAR EVENTO CALENDÁRIO
# =====================================================

@login_required
def criar_evento(request):

    # =================================================
    # APENAS DIRETOR
    # =================================================

    if request.user.role != "DIRETOR_PEDAGOGICO":

        messages.error(
            request,
            "Você não tem permissão para acessar esta área."
        )

        return redirect("dashboard")

    # =================================================
    # ESCOLA
    # =================================================

    escola = request.user.escola

    if not escola:

        messages.error(
            request,
            "Nenhuma escola associada ao usuário."
        )

        return redirect("dashboard")

    # =================================================
    # ANO LETIVO ATIVO
    # =================================================

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:

        messages.error(
            request,
            "Nenhum ano letivo ativo encontrado."
        )

        return redirect(
            "calendario_escolar"
        )

    # =================================================
    # POST
    # =================================================

    if request.method == "POST":

        form = CalendarioEscolarForm(
            request.POST
        )

        if form.is_valid():

            evento = form.save(commit=False)

            # =========================================
            # ATRIBUIÇÕES AUTOMÁTICAS
            # =========================================

            evento.escola = escola

            evento.ano_letivo = ano_letivo

            evento.criado_por = request.user

            # =========================================
            # EVENTO GERAL
            # =========================================

            if evento.turma:

                evento.evento_geral = False

            else:

                evento.evento_geral = True

            # =========================================
            # VALIDAÇÃO DE DATAS
            # =========================================

            if evento.data_fim:

                if evento.data_fim < evento.data_inicio:

                    messages.error(
                        request,
                        "A data final não pode ser menor que a data inicial."
                    )

                    return render(
                        request,
                        "criar_evento.html",
                        {
                            "form": form
                        }
                    )

            # =========================================
            # HORÁRIO
            # =========================================

            if evento.hora_inicio and evento.hora_fim:

                if evento.hora_fim < evento.hora_inicio:

                    messages.error(
                        request,
                        "A hora final não pode ser menor que a hora inicial."
                    )

                    return render(
                        request,
                        "criar_evento.html",
                        {
                            "form": form
                        }
                    )

            # =========================================
            # SALVAR
            # =========================================

            evento.save()

            # =========================================
            # FUTURO SISTEMA DE NOTIFICAÇÕES
            # =========================================

            if evento.enviar_notificacao:

                pass

                # Aqui futuramente:
                # enviar_notificacao_evento(evento)

            # =========================================
            # SUCESSO
            # =========================================

            messages.success(
                request,
                "Evento criado com sucesso."
            )

            return redirect(
                "calendario_escolar"
            )

        else:

            messages.error(
                request,
                "Corrija os erros do formulário."
            )

    # =================================================
    # GET
    # =================================================

    else:

        form = CalendarioEscolarForm()

    # =================================================
    # CONTEXT
    # =================================================

    context = {

        "form": form,

        "ano_letivo": ano_letivo,

    }

    # =================================================
    # RENDER
    # =================================================

    return render(
        request,
        "criar_evento.html",
        context
    )


# =====================================================
# CALENDÁRIO PROFESSOR
# =====================================================
from django.db.models import Q

@login_required
def calendario_professor(request):

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user

    # TURMAS DO PROFESSOR
    turmas = Turma.objects.filter(
        professor=professor
    )

    # EVENTOS
    eventos = CalendarioEscolar.objects.filter(

        ativo=True,
        mostrar_para_professor=True

    ).filter(

        Q(evento_geral=True) |
        Q(turma__in=turmas)

    ).distinct().order_by(
        "data_inicio"
    )

    context = {
        "eventos": eventos
    }

    return render(
        request,
        "calendario_professor.html",
        context
    )




# =====================================================
# CALENDÁRIO DO ALUNO
# =====================================================

@login_required
def calendario_aluno(request):

    if request.user.role != "ALUNO":
        return redirect("dashboard")

    # BUSCAR ALUNO
    aluno = Aluno.objects.filter(
        usuario=request.user
    ).first()

    # VALIDAÇÃO
    if not aluno:

        messages.error(
            request,
            "Aluno não encontrado."
        )

        return redirect("dashboard")

    # EVENTOS
    eventos = CalendarioEscolar.objects.filter(

        escola=aluno.escola,

        ativo=True,

        mostrar_para_aluno=True

    ).filter(

        Q(evento_geral=True) |

        Q(turma=aluno.turma)

    ).order_by(

        "data_inicio"

    )

    context = {

        "aluno": aluno,
        "eventos": eventos,

    }

    return render(

        request,

        "calendario_aluno.html",

        context

    )


# =====================================================
# CALENDÁRIO SECRETARIA
# =====================================================

@login_required
def calendario_secretaria(request):

    if request.user.role != "SECRETARIA":
        return redirect("dashboard")

    eventos = CalendarioEscolar.objects.filter(

        escola=request.user.escola,

        ativo=True,

        mostrar_para_secretaria=True

    ).order_by(

        "data_inicio"

    )

    context = {

        "eventos": eventos,

    }

    return render(

        request,

        "calendario_secretaria.html",

        context

    )




# =====================================================
# REGISTRAR PAGAMENTO MENSALIDADE
# =====================================================

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


@login_required
def registrar_pagamento_mensalidade(request, mensalidade_id):

    # =====================================================
    # PERMISSÃO
    # =====================================================

    if getattr(request.user, "role", None) != "SECRETARIA":
        return redirect("dashboard_secretaria")

    escola = request.user.escola

    # =====================================================
    # BUSCAR MENSALIDADE
    # =====================================================

    mensalidade = get_object_or_404(
        Mensalidade.objects.select_related(
            "aluno",
            "aluno__turma",
            "ano_letivo"
        ).prefetch_related(
            "pagamentos"
        ),
        id=mensalidade_id,
        aluno__escola=escola
    )

    # =====================================================
    # TOTAL PAGO
    # =====================================================

    total_pago = mensalidade.pagamentos.aggregate(
        total=Sum("valor_pago")
    )["total"] or Decimal("0.00")

    restante = mensalidade.valor - total_pago

    # =====================================================
    # SE JÁ ESTIVER PAGA
    # =====================================================

    if restante <= 0:

        mensalidade.atualizar_status()

        messages.info(
            request,
            "Esta mensalidade já está totalmente paga."
        )

        return redirect("mensalidades")

    # =====================================================
    # REGISTRO PAGAMENTO
    # =====================================================

    if request.method == "POST":

        valor_pago = request.POST.get("valor_pago")
        forma_pagamento = request.POST.get("forma_pagamento")
        observacao = request.POST.get("observacao", "").strip()
        referencia = request.POST.get("referencia", "").strip()

        # =====================================================
        # VALIDAR VALOR
        # =====================================================

        try:

            valor_pago = Decimal(valor_pago)

        except (InvalidOperation, TypeError):

            messages.error(
                request,
                "Valor inválido."
            )

            return redirect(
                "registrar_pagamento_mensalidade",
                mensalidade_id=mensalidade.id
            )

        # =====================================================
        # VALIDAÇÕES
        # =====================================================

        if valor_pago <= 0:

            messages.error(
                request,
                "O valor deve ser maior que zero."
            )

            return redirect(
                "registrar_pagamento_mensalidade",
                mensalidade_id=mensalidade.id
            )

        if valor_pago > restante:

            messages.error(
                request,
                f"O valor excede o restante da mensalidade ({restante} Kz)."
            )

            return redirect(
                "registrar_pagamento_mensalidade",
                mensalidade_id=mensalidade.id
            )

        # =====================================================
        # SALVAR PAGAMENTO
        # =====================================================

        try:

            with transaction.atomic():

                pagamento = Pagamento.objects.create(

                    aluno=mensalidade.aluno,

                    escola=escola,

                    mensalidade=mensalidade,

                    ano_letivo=mensalidade.ano_letivo,

                    tipo="MENSALIDADE",

                    valor_pago=valor_pago,

                    forma_pagamento=forma_pagamento,

                    referencia=referencia,

                    observacao=observacao,

                    recebido_por=request.user,

                    data_pagamento=timezone.now()

                )

                # Atualizar status automaticamente
                mensalidade.atualizar_status()

        except Exception as e:

            messages.error(
                request,
                f"Erro ao registrar pagamento: {str(e)}"
            )

            return redirect(
                "registrar_pagamento_mensalidade",
                mensalidade_id=mensalidade.id
            )

        # =====================================================
        # SUCESSO
        # =====================================================

        messages.success(
            request,
            f"Pagamento registrado com sucesso. Recibo Nº {pagamento.numero_recibo}"
        )

        return redirect("mensalidades")

    # =====================================================
    # HISTÓRICO DE PAGAMENTOS
    # =====================================================

    pagamentos = mensalidade.pagamentos.select_related(
        "recebido_por"
    ).order_by("-data_pagamento")

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "mensalidade": mensalidade,

        "total_pago": total_pago,

        "restante": restante,

        "pagamentos": pagamentos,

    }

    return render(
        request,
        "registrar_pagamento_mensalidade.html",
        context
    )


@login_required
def editar_turma(request, pk):

    turma = get_object_or_404(Turma, id=pk)

    cursos = Curso.objects.filter(
        escola=turma.escola
    ).order_by("nome")

    if request.method == "POST":

        turma.identificador = request.POST.get("identificador")
        turma.classe = request.POST.get("classe")
        turma.curso_id = request.POST.get("curso")

        turma.save()

        messages.success(
            request,
            "Turma atualizada com sucesso."
        )

        return redirect("turmas")

    return render(
        request,
        "editar_turma.html",
        {
            "turma": turma,
            "cursos": cursos,
        }
    )






# =========================================================
# LISTA MINI PAUTAS
# =========================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

from academic.models import (
    MiniPauta,
    Turma,
    Disciplina,
    Aluno,
    AnoLetivo
)


@login_required
def mini_pautas_lista(request):

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    if not ano_letivo:
        return redirect("dashboard")

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    trimestre = request.GET.get("trimestre")

    # ================================
    # FILTRO CORRIGIDO (ANO LETIVO)
    # ================================
    turmas = Turma.objects.filter(
        escola=escola,
        ano_letivo=ano_letivo,
        disciplinas__professor=professor
    ).distinct()

    disciplinas = Disciplina.objects.filter(
        professor=professor,
        escola=escola,
        turma__ano_letivo=ano_letivo
    ).select_related("turma").distinct()

    mini_pautas = MiniPauta.objects.filter(
        professor=professor,
        escola=escola,
        ano_letivo=ano_letivo
    ).select_related("turma", "disciplina", "aluno")

    if turma_id:
        mini_pautas = mini_pautas.filter(turma_id=turma_id)

    if disciplina_id:
        mini_pautas = mini_pautas.filter(disciplina_id=disciplina_id)

    if trimestre:
        mini_pautas = mini_pautas.filter(trimestre=int(trimestre))

    context = {
        "mini_pautas": mini_pautas,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
        "trimestre": trimestre,
        "ano_letivo": ano_letivo
    }

    return render(request, "mini_pautas_lista.html", context)


# =========================================================
# DETALHE MINI PAUTA
# =========================================================

@login_required
def mini_pauta_detalhe(request, pk):

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    mini_pauta_ref = get_object_or_404(
        MiniPauta,
        pk=pk,
        professor=request.user,
        escola=request.user.escola
    )

    alunos = Aluno.objects.filter(
        turma=mini_pauta_ref.turma,
        escola=request.user.escola,
        ativo=True
    ).order_by("numero_na_turma")

    mini_pautas_qs = MiniPauta.objects.filter(
        professor=request.user,
        escola=request.user.escola,
        turma=mini_pauta_ref.turma,
        disciplina=mini_pauta_ref.disciplina,
        ano_letivo=mini_pauta_ref.ano_letivo,
        trimestre=mini_pauta_ref.trimestre
    )

    # 🔥 MUITO MAIS SEGURO QUE DICT MANUAL
    mini_pautas_existentes = {
        mp.aluno_id: mp for mp in mini_pautas_qs
    }

    context = {
        "mini_pauta_ref": mini_pauta_ref,
        "alunos": alunos,
        "mini_pautas_existentes": mini_pautas_existentes,
    }

    return render(request, "mini_pauta_detalhe.html", context)


# =========================================================
# GERAR MINI PAUTAS
# =========================================================

@login_required
def gerar_mini_pautas(request):

    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    professor = request.user
    escola = professor.escola

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    trimestre = request.GET.get("trimestre")

    if not (turma_id and disciplina_id and trimestre):
        return redirect("mini_pautas")

    ano_letivo = AnoLetivo.objects.filter(
        escola=escola,
        ativo=True
    ).first()

    turma = get_object_or_404(Turma, id=turma_id, escola=escola)
    disciplina = get_object_or_404(
        Disciplina,
        id=disciplina_id,
        escola=escola,
        turma__ano_letivo=ano_letivo
    )

    alunos = Aluno.objects.filter(
        turma=turma,
        escola=escola,
        ativo=True
    )

    for aluno in alunos:

        MiniPauta.objects.get_or_create(
            professor=professor,
            escola=escola,
            aluno=aluno,
            turma=turma,
            disciplina=disciplina,
            ano_letivo=ano_letivo,
            trimestre=int(trimestre)
        )

    return redirect("mini_pautas")


# =========================================================
# SALVAR MINI PAUTA
# =========================================================

from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

@login_required
def salvar_mini_pauta_turma(request, pk):

    # =========================
    # PERMISSÃO
    # =========================
    if request.user.role != "PROFESSOR":
        return redirect("dashboard")

    mini_pauta_ref = get_object_or_404(
        MiniPauta,
        pk=pk,
        professor=request.user,
        escola=request.user.escola
    )

    # =========================
    # BLOQUEIO SE FECHADO
    # =========================
    if getattr(mini_pauta_ref, "trimestre_fechado", False):
        return redirect("mini_pauta_detalhe", pk=pk)

    if request.method != "POST":
        return redirect("mini_pauta_detalhe", pk=pk)

    # =========================
    # ALUNOS DA TURMA
    # =========================
    alunos = Aluno.objects.filter(
        turma=mini_pauta_ref.turma,
        escola=request.user.escola,
        ativo=True
    ).order_by("numero_na_turma")

    # =========================
    # CONVERSÃO SEGURA
    # =========================
    def parse_decimal(value):
        """
        Converte:
        '12,0' -> 12.0
        ' 14 ' -> 14.0
        '' -> None
        """
        if value in [None, ""]:
            return None

        value = str(value).strip().replace(",", ".")

        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    def get_value(aluno, campo):
        return parse_decimal(request.POST.get(f"{campo}_{aluno.id}"))

    # =========================
    # UPDATE INTELIGENTE
    # =========================
    for aluno in alunos:

        obj, _ = MiniPauta.objects.get_or_create(
            professor=mini_pauta_ref.professor,
            escola=mini_pauta_ref.escola,
            aluno=aluno,
            turma=mini_pauta_ref.turma,
            disciplina=mini_pauta_ref.disciplina,
            ano_letivo=mini_pauta_ref.ano_letivo,
            trimestre=int(mini_pauta_ref.trimestre)
        )

        # =========================
        # NOTAS (SÓ ATUALIZA SE EXISTIR VALOR)
        # =========================

        campos = [
            "av1", "av2", "av3", "p1",
            "av4", "av5", "av6", "p2",
            "exame", "recurso"
        ]

        for campo in campos:
            valor = get_value(aluno, campo)
            if valor is not None:
                setattr(obj, campo, valor)

        obj.save()

    return redirect("mini_pauta_detalhe", pk=pk)



@login_required
def fechar_trimestre(request, pk):

    mp = get_object_or_404(
        MiniPauta,
        pk=pk,
        professor=request.user,
        escola=request.user.escola
    )

    mp.trimestre_fechado = True
    mp.save()

    return redirect("mini_pauta_detalhe", pk=pk)


from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def mini_pauta_pdf(request, pk):

    mini_pauta_ref = get_object_or_404(
        MiniPauta,
        pk=pk,
        professor=request.user,
        escola=request.user.escola
    )

    alunos = Aluno.objects.filter(
        turma=mini_pauta_ref.turma,
        escola=request.user.escola,
        ativo=True
    ).order_by("numero_na_turma")

    mini_pautas_existentes = {
        mp.aluno.id: mp
        for mp in MiniPauta.objects.filter(
            professor=mini_pauta_ref.professor,
            escola=mini_pauta_ref.escola,
            turma=mini_pauta_ref.turma,
            disciplina=mini_pauta_ref.disciplina,
            ano_letivo=mini_pauta_ref.ano_letivo,
            trimestre=mini_pauta_ref.trimestre,
        )
    }

    html = render_to_string("mini_pauta_pdf.html", {
        "mini_pauta_ref": mini_pauta_ref,
        "alunos": alunos,
        "mini_pautas_existentes": mini_pautas_existentes,
    })

    return HttpResponse(html)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from academic.models import (
    AnoLetivo,
    Turma,
    Disciplina,
    Aluno,
    Nota,
)


@login_required
def pauta_final_ano(request):

    # =====================================================
    # PERMISSÕES
    # =====================================================

    if request.user.role not in [
        "DIRETOR",
        "DIRETOR_PEDAGOGICO",
        "SUPERADMIN",
    ]:
        return redirect("dashboard")

    escola = request.user.escola

    # =====================================================
    # FILTROS
    # =====================================================

    ano_letivo_id = request.GET.get("ano_letivo")
    turma_id = request.GET.get("turma")

    anos_letivos = AnoLetivo.objects.filter(
        escola=escola
    ).order_by("-nome")

    turmas = Turma.objects.filter(
        escola=escola
    ).select_related(
        "curso",
        "ano_letivo",

    )

    pauta = []
    disciplinas = []
    turma = None
    estatisticas = None

    # =====================================================
    # GERAR PAUTA
    # =====================================================

    if ano_letivo_id and turma_id:

        ano_letivo = get_object_or_404(
            AnoLetivo,
            id=ano_letivo_id,
            escola=escola,
        )

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola,
        )

        # =====================================================
        # NOTA MÍNIMA DA CLASSE
        # =====================================================

        try:
            if hasattr(turma.classe, "ordem") and turma.classe.ordem is not None:
                numero_classe = int(turma.classe.ordem)
            else:
                numero_classe = int(
                    "".join(filter(str.isdigit, turma.classe.nome))
                )
        except (ValueError, TypeError, AttributeError):
            numero_classe = 7

        nota_minima = 5 if numero_classe <= 6 else 10

        # =====================================================

        disciplinas = list(
            Disciplina.objects.filter(
                turma=turma
            ).order_by("nome")
        )

        alunos = (
            Aluno.objects.filter(
                turma=turma,
                ativo=True,
            )
            .select_related("usuario")
            .order_by(
                "numero_na_turma",
                "usuario__first_name",
            )
        )

        notas = Nota.objects.filter(
            aluno__in=alunos,
            disciplina__in=disciplinas,
            ano_letivo=ano_letivo,
        )

        notas_map = {}

        for nota in notas:
            notas_map[
                (nota.aluno_id, nota.disciplina_id, nota.trimestre)
            ] = nota

        # =====================================================
        # ESTATÍSTICAS
        # =====================================================

        total_aprovados = 0
        total_recurso = 0
        total_reprovados = 0

        # =====================================================
        # MONTAR PAUTA
        # =====================================================

        for aluno in alunos:

            linha = {
                "aluno": aluno,
                "disciplinas": [],
                "negativas": 0,
                "disciplinas_recurso": [],
                "media_geral": 0,
                "situacao": "",
            }

            medias_finais = []

            for disciplina in disciplinas:

                n1 = notas_map.get((aluno.id, disciplina.id, 1))
                n2 = notas_map.get((aluno.id, disciplina.id, 2))
                n3 = notas_map.get((aluno.id, disciplina.id, 3))

                # =============================================
                # AUSÊNCIA DE NOTA = 0
                # =============================================

                m1 = float(n1.media_final) if n1 and n1.media_final is not None else 0
                m2 = float(n2.media_final) if n2 and n2.media_final is not None else 0
                m3 = float(n3.media_final) if n3 and n3.media_final is not None else 0

                mf = round((m1 + m2 + m3) / 3, 1)

                medias_finais.append(mf)

                # =============================================
                # NEGATIVAS
                # =============================================

                if mf < nota_minima:
                    linha["negativas"] += 1
                    linha["disciplinas_recurso"].append(
                        disciplina.nome
                    )

                linha["disciplinas"].append({
                    "disciplina": disciplina,
                    "m1": m1,
                    "m2": m2,
                    "m3": m3,
                    "mf": mf,
                })

            # =====================================================
            # MÉDIA GERAL
            # =====================================================

            if medias_finais:
                linha["media_geral"] = round(
                    sum(medias_finais) / len(medias_finais),
                    1,
                )
            else:
                linha["media_geral"] = 0

            # =====================================================
            # SITUAÇÃO FINAL
            # =====================================================

            if linha["negativas"] == 0:
                linha["situacao"] = "APROVADO"
                total_aprovados += 1

            elif linha["negativas"] <= 3:
                linha["situacao"] = "RECURSO"
                total_recurso += 1

            else:
                linha["situacao"] = "REPROVADO"
                total_reprovados += 1

            pauta.append(linha)

        # =====================================================
        # RANKING
        # =====================================================

        pauta.sort(
            key=lambda x: x["media_geral"],
            reverse=True,
        )

        for posicao, linha in enumerate(
            pauta,
            start=1,
        ):
            linha["posicao"] = posicao

        # =====================================================
        # ESTATÍSTICAS
        # =====================================================

        total_alunos = len(pauta)

        estatisticas = {
            "total_alunos": total_alunos,
            "aprovados": total_aprovados,
            "recurso": total_recurso,
            "reprovados": total_reprovados,
            "percentual_aprovacao": round(
                (total_aprovados / total_alunos) * 100,
                2,
            ) if total_alunos else 0,
            "nota_minima": nota_minima,
        }

    # =====================================================
    # CONTEXT
    # =====================================================

    return render(
        request,
        "pauta_final_ano.html",
        {
            "anos_letivos": anos_letivos,
            "turmas": turmas,
            "turma": turma,
            "disciplinas": disciplinas,
            "pauta": pauta,
            "estatisticas": estatisticas,
            "ano_letivo_id": ano_letivo_id,
            "turma_id": turma_id,
        },
    )

