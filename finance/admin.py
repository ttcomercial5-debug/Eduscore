from django.contrib import admin
from academic.models import Plano, PagamentoPlano

@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = (
    "nome",
    "valor_mensal",
    "limite_alunos",
    "ativo",
    )
    list_filter = ("ativo",)
    search_fields = ("nome",)

@admin.register(PagamentoPlano)
class PagamentoPlanoAdmin(admin.ModelAdmin):
    list_display = (
    "escola",
    "valor",
    "data_vencimento",
    "data_pagamento",
    "status",
    "criado_em",
    )
    list_filter = ("status",)
    search_fields = ("escola__nome",)
