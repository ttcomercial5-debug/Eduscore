from django.shortcuts import redirect
from django.utils import timezone


# =====================================================
# CONTROLE DE ATIVAÇÃO DA ESCOLA
# =====================================================

class EscolaAtivaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Páginas livres
        urls_livres = [
            "/login/",
            "/logout/",
            "/bloqueado/",
        ]

        if request.path in urls_livres:
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        # SUPERADMIN nunca é bloqueado
        if request.user.role == "SUPERADMIN":
            return self.get_response(request)

        escola = getattr(request.user, "escola", None)

        # Usuário sem escola
        if not escola:
            return redirect("login")

        # Escola inativa
        if not escola.ativo:
            return redirect("bloqueado")

        # Plano associado à escola
        plano = escola.plano

        # Se existir plano e ele estiver inativo
        if plano and not plano.ativo:
            return redirect("bloqueado")

        # Verificar vencimento da assinatura da escola
        if (
            escola.data_expiracao
            and escola.data_expiracao < timezone.now().date()
        ):
            return redirect("bloqueado")

        return self.get_response(request)


# =====================================================
# BLOQUEAR ACESSO AO DJANGO ADMIN
# =====================================================

class AdminRestritoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/admin"):

            if not request.user.is_authenticated:
                return redirect("login")

            # Apenas SUPERADMIN pode entrar
            if request.user.role != "SUPERADMIN":
                return redirect("dashboard")

        return self.get_response(request)