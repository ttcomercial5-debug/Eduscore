from django.shortcuts import redirect
from django.utils import timezone
from academic.models import Plano


# =====================================================
# 1️⃣ CONTROLE DE ATIVAÇÃO DA ESCOLA
# =====================================================

class EscolaAtivaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Permitir páginas livres
        urls_livres = [
            '/login/',
            '/logout/',
            '/bloqueado/',
        ]

        if request.path in urls_livres:
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        # 🔥 SUPERADMIN nunca é bloqueado
        if request.user.role == 'SUPERADMIN':
            return self.get_response(request)

        escola = request.user.escola

        # Se não tiver escola → volta login
        if not escola:
            return redirect('login')

        # Escola inativa
        if not escola.ativo:
            return redirect('bloqueado')

        # Verificar plano
        plano = Plano.objects.filter(escola=escola).first()

        # Se não tiver plano → permitir acesso (modo teste)
        if not plano:
            return self.get_response(request)

        # Só bloqueia se plano existir e estiver vencido
        if plano.data_expiracao:
            if plano.data_expiracao < timezone.now().date():
                return redirect('bloqueado')

        return self.get_response(request)


# =====================================================
# 2️⃣ BLOQUEAR ACESSO AO DJANGO ADMIN
# =====================================================

class AdminRestritoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith('/admin'):

            if not request.user.is_authenticated:
                return redirect('login')

            # 🔒 Apenas SUPERADMIN pode entrar no admin
            if request.user.role != 'SUPERADMIN':
                return redirect('dashboard')

        return self.get_response(request)