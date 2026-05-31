from datetime import date
from decimal import Decimal
from django.utils import timezone

from academic.models import Mensalidade

MESES_ANO_ESCOLAR = [
    ("Agosto", 8),
    ("Setembro", 9),
    ("Outubro", 10),
    ("Novembro", 11),
    ("Dezembro", 12),
    ("Janeiro", 1),
    ("Fevereiro", 2),
    ("Março", 3),
    ("Abril", 4),
    ("Maio", 5),
]


def gerar_mensalidades_aluno(aluno, ano_letivo, valor):

    ano_inicio = int(ano_letivo.nome.split("/")[0])
    ano_fim = int(ano_letivo.nome.split("/")[1])

    for mes_nome, mes_numero in MESES_ANO_ESCOLAR:

        if mes_numero >= 8:
            ano = ano_inicio
        else:
            ano = ano_fim

        vencimento = date(ano, mes_numero, 10)

        Mensalidade.objects.get_or_create(
            aluno=aluno,
            ano_letivo=ano_letivo,
            mes=mes_nome,
            defaults={
                "valor": valor,
                "vencimento": vencimento
            }
        )


def atualizar_mensalidades():

    mensalidades = Mensalidade.objects.all()

    for m in mensalidades:
        m.atualizar_status()


def calcular_valor_com_multa(mensalidade):

    multa_percentual = Decimal("0.10")  # 10%

    if mensalidade.status == "ATRASADA":
        multa = mensalidade.valor * multa_percentual
        return mensalidade.valor + multa

    return mensalidade.valor
