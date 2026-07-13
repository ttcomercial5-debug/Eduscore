from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
from academic.models import (
    CalendarioEscolar,
    HistoricoAcademico,
    HistoricoMatricula
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            'Informação pessoal',
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'email',
                    'telefone',
                )
            },
        ),
        (
            'Perfil',
            {
                'fields': (
                    'role',
                    'ativo',
                    'escola',
                )
            },
        ),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (
            'Datas importantes',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'password1',
                    'password2',
                    'first_name',
                    'last_name',
                    'email',
                    'telefone',
                    'role',
                    'ativo',
                    'escola',
                ),
            },
        ),
    )

    list_display = (
        'username',
        'email',
        'telefone',
        'role',
        'escola',
        'ativo',
        'is_staff',
    )

    list_filter = (
        'role',
        'ativo',
        'is_staff',
        'escola',
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email',
        'telefone',
    )

    ordering = ('username',)


# ==========================================================
# CALENDÁRIO ESCOLAR
# ==========================================================

@admin.register(CalendarioEscolar)
class CalendarioEscolarAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "tipo",
        "data_inicio",
        "escola"
    )

    list_filter = (
        "tipo",
        "escola"
    )

    search_fields = (
        "titulo",
    )


# ==========================================================
# HISTÓRICO ACADÉMICO
# ==========================================================

@admin.register(HistoricoAcademico)
class HistoricoAcademicoAdmin(admin.ModelAdmin):

    list_display = (
        "aluno",
        "ano_letivo",
        "classe",
        "turma",
        "situacao",
        "criado_em",
    )

    list_filter = (
        "ano_letivo",
        "classe",
        "situacao",
    )

    search_fields = (
        "aluno__usuario__first_name",
        "aluno__numero_processo",
    )

@admin.register(HistoricoMatricula)
class HistoricoMatriculaAdmin(admin.ModelAdmin):

    list_display = (
        "aluno",
        "ano_letivo",
        "classe",
        "turma",
        "curso",
        "numero_na_turma",
    )

    list_filter = (
        "ano_letivo",
        "classe",
        "curso",
    )

    search_fields = (
        "aluno__usuario__first_name",
        "aluno__numero_processo",
        "matricula",
    )