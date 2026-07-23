from decimal import Decimal

from django.db import transaction

from academic.models import (
    Aluno,
    Mensalidade,
    AnoLetivo
)

from academic.models import ConfiguracaoMensalidade



MESES = [

    ("09","Setembro"),
    ("10","Outubro"),
    ("11","Novembro"),
    ("12","Dezembro"),
    ("01","Janeiro"),
    ("02","Fevereiro"),
    ("03","Março"),
    ("04","Abril"),
    ("05","Maio"),
    ("06","Junho"),

]




@transaction.atomic
def gerar_mensalidades_escola(
        escola,
        ano_letivo
):


    alunos = Aluno.objects.filter(
        escola=escola,
        ativo=True
    ).select_related(
        "turma",
        "turma__curso"
    )



    criadas = 0



    for aluno in alunos:


        turma = aluno.turma


        if not turma:
            continue



        classe = str(
            turma.classe
        )



        curso = getattr(
            turma,
            "curso",
            None
        )



        configuracao = ConfiguracaoMensalidade.obter_configuracao(

            escola,

            classe,

            curso

        )



        if not configuracao:

            continue



        valor = configuracao.valor



        for numero, nome_mes in MESES:



            existe = Mensalidade.objects.filter(

                aluno=aluno,

                ano_letivo=ano_letivo,

                mes=numero

            ).exists()



            if existe:

                continue



            Mensalidade.objects.create(

                aluno=aluno,

                escola=escola,

                ano_letivo=ano_letivo,

                mes=numero,

                valor=valor,

                status="PENDENTE"

            )



            criadas +=1



    return criadas