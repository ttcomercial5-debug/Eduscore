"""
URL configuration for school_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# ViewSets da API
from academic.views import (
    TurmaViewSet,
    DisciplinaViewSet,
    AlunoViewSet,
    NotaViewSet,
    FrequenciaViewSet,
    TarefaViewSet,
)

# Router API
router = DefaultRouter()
router.register(r'turmas', TurmaViewSet)
router.register(r'disciplinas', DisciplinaViewSet)
router.register(r'alunos', AlunoViewSet)
router.register(r'notas', NotaViewSet)
router.register(r'frequencias', FrequenciaViewSet)
router.register(r'tarefas', TarefaViewSet)

urlpatterns = [

    # Admin Django
    path('admin/', admin.site.urls),

    # =========================
    # WEB APP (Templates)
    # =========================
    path('', include('core.urls')),

    # =========================
    # AUTENTICAÇÃO DJANGO
    # (Login, Logout, Password Change)
    # =========================


    # =========================
    # API JWT
    # =========================
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # =========================
    # API REST
    # =========================
    path('api/', include(router.urls)),
]