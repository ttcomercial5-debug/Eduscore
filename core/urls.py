from django.conf import settings
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.shortcuts import redirect

def home(request):
    return redirect('login')

urlpatterns = [

    path('', views.login_view, name='home'),

    # =============================
    # AUTH
    # =============================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('recuperar-senha/', views.esqueci_senha, name='esqueci_senha'),
    path("recuperar/confirmar-otp/", views.confirmar_otp_recuperacao, name="confirmar_otp_recuperacao"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('bloqueado/', views.bloqueado, name='bloqueado'),
    path("alterar-senha/", views.alterar_senha, name="alterar_senha"),
    path("diretor-pedagogico/dashboard/", views.dashboard_diretor_pedagogico, name="dashboard_diretor_pedagogico"),
    path("secretaria/alterar-senha/", views.alterar_senha_secretaria, name="alterar_senha_secretaria"),
    path("financeiro/alterar-senha/", views.alterar_senha_financeiro, name="alterar_senha_financeiro"),
    path("professor/alterar-senha/", views.alterar_senha_professor, name="alterar_senha_professor"),
    path("aluno/alterar-senha/", views.alterar_senha_aluno, name="alterar_senha_aluno"),
    path("professor/turma/<int:turma_id>/disciplina/<int:disciplina_id>/frequencia/", views.marcar_frequencia, name="marcar_frequencia",),



    # =============================
    # ESCOLAS
    # =============================
    path('escolas/', views.lista_escolas, name='escolas'),
    path('escolas/', views.lista_escolas, name='lista_escolas'),
    path('escolas/selecionar/<int:escola_id>/', views.selecionar_escola, name='selecionar_escola'),
    path('escolas/eliminar/<int:escola_id>/', views.eliminar_escola, name='eliminar_escola'),
    path('planos/', views.gerenciar_planos, name='gerenciar_planos'),
    path("planos/editar/<int:plano_id>/", views.editar_plano, name="editar_plano"),
    path("planos/excluir/<int:plano_id>/", views.excluir_plano, name="excluir_plano"),
    path('pagamentos-escolas/', views.gerenciar_pagamentos, name='gerenciar_pagamentos'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path("calendario/", views.calendario_escolar, name="calendario_escolar"),
    path("calendario/novo/", views.criar_evento, name="criar_evento"),
    path("cursos/editar/<int:curso_id>/", views.editar_curso, name="editar_curso"),
    path("cursos/eliminar/<int:curso_id>/", views.eliminar_curso, name="eliminar_curso"),
    path('pagamentos/editar/<int:pagamento_id>/', views.editar_pagamento, name='editar_pagamento'),
    path('pagamento/deletar/<int:id>/', views.deletar_pagamento, name='deletar_pagamento'),

    # =============================
    # ALUNOS
    # =============================
    path('alunos/', views.lista_alunos, name='alunos'),
    path('alunos/adicionar/', views.adicionar_aluno, name='adicionar_aluno'),
    path('aluno/dashboard/', views.dashboard_aluno, name='dashboard_aluno'),
    path('aluno/boletim/', views.gerar_boletim_pdf, name='boletim_pdf'),
    path('aluno/horario/', views.horario_aluno, name='horario_aluno'),
    path("notas/", views.notas_aluno, name="notas_aluno"),
    path("validar-boletim/<str:codigo>/", views.validar_boletim, name="validar_boletim"),
    path("buscar-aluno/", views.buscar_aluno_por_processo, name="buscar_aluno"),
    path("alunos/editar/<int:aluno_id>/", views.editar_aluno, name="editar_aluno"),
    path("alunos/eliminar/<int:aluno_id>/", views.eliminar_aluno, name="eliminar_aluno"),
    path('alunos/financeiro/', views.situacao_financeira, name='situacao_financeira'),
    path("aluno/historico/", views.historico_academico, name="historico_academico"),
    path("aluno/calendario/", views.calendario_aluno, name="calendario_aluno"),
    path("aluno/frequencias/", views.frequencia_aluno, name="frequencia_aluno"),
    path("aluno/boletim/<int:historico_id>/", views.boletim_historico_pdf, name="boletim_historico_pdf"),


    # =============================
    # PROFESSORES
    # =============================
    path('professores/', views.lista_professores, name='professores'),
    path('professores/adicionar/', views.adicionar_professor, name='adicionar_professor'),
    path("professor/historico/", views.historico_professor, name="historico_professor"),
    path('dashboard/professor/', views.dashboard_professor, name='dashboard_professor'),
    path("professor/turmas/", views.minhas_turmas, name="minhas_turmas"),
    path("professor/lancar-notas/", views.lancar_notas, name="lancar_notas"),
    path("professor/relatorios/", views.relatorios_professor, name="relatorios_professor"),
    path('professor/calendario/', views.calendario_professor, name='calendario_professor'),
    path("historico-notas/", views.historico_notas, name="historico_notas"),
    path("professor/turma/<int:turma_id>/alunos/", views.alunos_da_turma, name="alunos_da_turma"),
    path("mini-pauta/fechar/<int:pk>/", views.fechar_trimestre, name="fechar_trimestre"),
    path("mini-pauta/pdf/<int:pk>/", views.mini_pauta_pdf, name="mini_pauta_pdf"),

    # =========================
    # MINI PAUTAS
    # =========================
    path("professor/mini-pautas/", views.mini_pautas_lista, name="mini_pautas"),
    path("professor/mini-pautas/<int:pk>/", views.mini_pauta_detalhe, name="mini_pauta_detalhe"),

    # avaliações
    path("professor/mini-pautas/gerar/", views.gerar_mini_pautas, name="gerar_mini_pautas"),
    path("mini-pauta/<int:pk>/salvar/", views.salvar_mini_pauta_turma, name="salvar_mini_pauta_turma"),

    # =============================
    # TURMAS & DISCIPLINAS
    # =============================
    path('turmas/', views.lista_turmas, name='turmas'),
    path('turmas/adicionar/', views.adicionar_turma, name='adicionar_turma'),
    path("disciplinas/<int:pk>/editar/", views.editar_disciplina, name="editar_disciplina"),
    path('disciplinas/', views.lista_disciplinas, name='disciplinas'),
    path('disciplinas/adicionar/', views.adicionar_disciplina, name='adicionar_disciplina'),
    path("turmas/<int:pk>/editar/", views.editar_turma, name="editar_turma"),
    path("promover-alunos/<int:ano_id>/", views.promover_alunos, name="promover_alunos"),
    path("diretor/turma/<int:turma_id>/imprimir/", views.imprimir_lista_turma, name="imprimir_lista_turma"),
    path("horarios/", views.horarios_turma, name="horarios_turma"),
    path("horarios/adicionar/<int:horario_id>/", views.adicionar_aula, name="adicionar_aula"),

    # =============================
    # DIRETOR
    # =============================
    path('painel-diretor/', views.painel_diretor, name='painel_diretor'),
    path('cadastrar-secretaria/', views.cadastrar_secretaria, name='cadastrar_secretaria'),
    path("diretor/alunos/", views.painel_diretor_alunos, name="painel_diretor_alunos"),
    path("professor/eliminar/<int:id>/", views.eliminar_professor, name="eliminar_professor"),
    path("diretor/cursos/", views.cursos, name="cursos"),
    path("diretor/frequencias/", views.painel_diretor_frequencia, name="painel_diretor_frequencia"),
    path('trimestre/toggle/<int:trimestre_id>/', views.toggle_trimestre, name='toggle_trimestre'),
    path("download-encerramento-pdf/", views.download_pdf_encerramento, name="download_pdf_encerramento"),
    path("pauta-final/", views.pauta_final_ano, name="pauta_final_ano"),
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path("notificacoes/lida/<int:id>/", views.marcar_notificacao_lida, name="notificacao_lida"),



    # =============================
    # SECRETARIA
    # =============================
    path('secretaria/dashboard', views.dashboard_secretaria, name='dashboard_secretaria'),
    path('secretaria/', views.secretaria, name='secretaria'),
    path('secretaria/mensalidades/', views.lista_mensalidades, name='mensalidades'),
    path('secretarias/', views.lista_secretarias, name='lista_secretarias'),
    path('secretarias/eliminar/<int:id>/', views.eliminar_secretaria, name='eliminar_secretaria'),
    # registrar pagamento de mensalidade específica
    path('secretaria/pagamento/mensalidade/<int:mensalidade_id>/', views.registrar_pagamento_mensalidade, name='registrar_pagamento_mensalidade'),

    # registrar pagamento geral (matrícula, uniforme, etc)
    path('secretaria/pagamento/novo/', views.registrar_pagamento, name='registrar_pagamento'),
    path('secretaria/pagamentos/', views.lista_pagamentos, name='pagamentos'),
    path("secretaria/matricula/confirmar/", views.confirmar_matricula, name="confirmar_matricula"),
    path("matricula/", views.criar_matricula, name="criar_matricula"),
    path("mensalidades/", views.lista_mensalidades, name="lista_mensalidades"),
    path("mensalidades/nova/", views.nova_mensalidade, name="nova_mensalidade"),
    path("secretaria/configuracao-financeira/", views.configuracao_financeira, name="configuracao_financeira"),
    path('secretaria/relatorio-mensalidades/', views.relatorio_mensalidades, name='relatorio_mensalidades'),
    path("secretaria/relatorio-turma-pdf/", views.exportar_estado_turma_pdf, name="exportar_estado_turma_pdf"),
    path("recibo/<int:pagamento_id>/", views.gerar_recibo, name="gerar_recibo"),
    path("recibo/", views.recibo_pagamento, name="recibo_pagamento"),
    path("secretaria/calendario/", views.calendario_secretaria, name="calendario_secretaria"),


#=============================================================
#FINANCEIRO
#=============================================================
    path("financeiro/", views.dashboard_financeiro, name="dashboard_financeiro"),
    path("pagamento/novo/", views.registrar_pagamento, name="registrar_pagamento"),
    path("recibo/<int:pagamento_id>/", views.recibo_pagamento, name="recibo_pagamento"),
    path("caixa/", views.caixa_diario, name="caixa_diario"),
    path("despesa/nova/", views.adicionar_despesa, name="adicionar_despesa"),
    path("financeiro/entradas/", views.entradas_financeiro, name="entradas_financeiro"),
    path("financeiro/entradas/nova/", views.adicionar_entrada, name="adicionar_entrada"),
    path("financeiro/despesas/", views.lista_despesas, name="lista_despesas"),
    path("financeiro/despesa/excluir/<int:id>/", views.excluir_despesa, name="excluir_despesa"),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

