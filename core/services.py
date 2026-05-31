from django.db.models import Avg
from academic.models import Aluno, Nota


def calcular_media_anual(aluno, ano_letivo):
    """
    Calcula média anual do aluno baseado no ano letivo
    """

    notas = Nota.objects.filter(
        aluno=aluno,
        ano_letivo=ano_letivo
    )

    if not notas.exists():
        return 0

    media = notas.aggregate(media=Avg("valor"))["media"]

    return round(media, 2) if media else 0


def promover_alunos(escola, ano_letivo):
    """
    Promove automaticamente alunos com média >= 10
    """

    alunos = Aluno.objects.filter(escola=escola)

    promovidos = 0

    for aluno in alunos:

        media = calcular_media_anual(aluno, ano_letivo)

        if media >= 10:
            try:
                nova_classe = str(int(aluno.classe) + 1)
                aluno.classe = nova_classe
                aluno.save()
                promovidos += 1
            except:
                pass

    return promovidos



from django.db.models import Sum
from django.utils import timezone
from academic.models import Mensalidade, Pagamento

def dados_financeiros_da_secretaria(escola):
    hoje = timezone.now().date()

    # Atualiza mensalidades vencidas
    Mensalidade.objects.filter(
        aluno__escola=escola,
        vencimento__lt=hoje,
        status="PENDENTE"
    ).update(status="ATRASADA")

    mensalidades = Mensalidade.objects.filter(aluno__escola=escola)
    pagamentos = Pagamento.objects.filter(aluno__escola=escola)

    total_recebido = pagamentos.aggregate(total=Sum("valor_pago"))["total"] or 0
    total_divida = mensalidades.filter(status__in=["PENDENTE", "ATRASADA"]).aggregate(total=Sum("valor"))["total"] or 0
    alunos_devedores = mensalidades.filter(status__in=["PENDENTE", "ATRASADA"]).values("aluno_id").distinct().count()

    mes_atual = hoje.month
    ano_atual = hoje.year
    total_mes = pagamentos.filter(
        data_pagamento__month=mes_atual,
        data_pagamento__year=ano_atual
    ).aggregate(total=Sum("valor_pago"))["total"] or 0

    total_mensalidades = mensalidades.count()
    mensalidades_divida = mensalidades.filter(status__in=["PENDENTE", "ATRASADA"]).count()
    taxa_inadimplencia = round((mensalidades_divida / total_mensalidades) * 100, 2) if total_mensalidades else 0

    ultimos_pagamentos = pagamentos.order_by("-data_pagamento")[:10]

    return {
        "total_recebido": total_recebido,
        "total_divida": total_divida,
        "alunos_devedores": alunos_devedores,
        "total_mes": total_mes,
        "ultimos_pagamentos": ultimos_pagamentos,
        "taxa_inadimplencia": taxa_inadimplencia,
    }