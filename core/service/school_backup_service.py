import json
import shutil
import tarfile

from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.core.serializers import serialize

from academic.models import (
    Escola,
    AnoLetivo,
    Turma,
    Disciplina,
    Aluno,
    Nota,
    Frequencia,
    Professor,
    Horario,
    HorarioTurma,
    AulaHorario,
    Mensalidade,
    Pagamento,
    HistoricoMatricula,
    HistoricoAcademico,
    ConfiguracaoFinanceira,
    Curso,
    Despesa,
    Entrada,
    CalendarioEscolar,
    Trimestre,
    FechamentoNota,
    FechamentoTrimestre,
    MiniPauta,
    Notificacao,
)

from users.models import User



class SchoolBackupService:
    """
    Backup individual por escola - EdusCel SaaS
    """

    def __init__(self):

        self.base_backup = (
            Path(settings.BASE_DIR)
            / "backups"
            / "escolas"
        )

        self.base_backup.mkdir(
            parents=True,
            exist_ok=True
        )


    def executar(self):

        print()
        print("=" * 50)
        print("BACKUP INDIVIDUAL POR ESCOLA - EDUSCEL")
        print("=" * 50)


        escolas = Escola.objects.all().order_by(
            "nome"
        )


        if not escolas.exists():

            print(
                "Nenhuma escola encontrada."
            )

            return


        for escola in escolas:

            try:

                self.backup_escola(
                    escola
                )


            except Exception as e:

                print(
                    f"ERRO {escola.nome}: {e}"
                )


        print()
        print(
            "✓ Todos backups concluídos."
        )



    def backup_escola(
        self,
        escola
    ):


        print(
            f"\nBackup: {escola.nome}"
        )


        pasta = self.criar_pastas(
            escola
        )


        self.exportar_dados(
            escola,
            pasta
        )


        self.exportar_info(
            escola,
            pasta
        )


        self.copiar_media(
            escola,
            pasta
        )


        arquivo = self.compactar_backup(
            escola,
            pasta
        )


        shutil.rmtree(
            pasta
        )


        print(
            f"✓ Criado: {arquivo}"
        )



    def criar_pastas(
        self,
        escola
    ):


        agora = datetime.now()


        nome = (
            escola.nome
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )


        pasta = (
            self.base_backup
            /
            nome
            /
            str(agora.year)
            /
            f"{agora.month:02d}"
            /
            agora.strftime(
                "%Y-%m-%d_%H-%M-%S"
            )
        )


        (pasta / "dados").mkdir(
            parents=True,
            exist_ok=True
        )


        (pasta / "media").mkdir(
            parents=True,
            exist_ok=True
        )


        return pasta




    def exportar_dados(
        self,
        escola,
        pasta
    ):


        modelos = {

            "usuarios": User.objects.filter(
                escola=escola
            ),


            "professores": Professor.objects.filter(
                escola=escola
            ),


            "alunos": Aluno.objects.filter(
                escola=escola
            ),


            "turmas": Turma.objects.filter(
                escola=escola
            ),


            "disciplinas": Disciplina.objects.filter(
                escola=escola
            ),


            "anos_letivos": AnoLetivo.objects.filter(
                escola=escola
            ),


            "notas": Nota.objects.filter(
                aluno__escola=escola
            ),


            "frequencias": Frequencia.objects.filter(
                escola=escola
            ),


            "horarios": Horario.objects.filter(
                escola=escola
            ),


            "horarios_turma": HorarioTurma.objects.filter(
                turma__escola=escola
            ),


            "aulas_horario": AulaHorario.objects.filter(
                horario__turma__escola=escola
            ),


            "mensalidades": Mensalidade.objects.filter(
                aluno__escola=escola
            ),


            "pagamentos": Pagamento.objects.filter(
                escola=escola
            ),


            "historico_matricula": HistoricoMatricula.objects.filter(
                aluno__escola=escola
            ),


            "historico_academico": HistoricoAcademico.objects.filter(
                aluno__escola=escola
            ),


            "config_financeira": ConfiguracaoFinanceira.objects.filter(
                escola=escola
            ),


            "cursos": Curso.objects.filter(
                escola=escola
            ),


            "despesas": Despesa.objects.filter(
                escola=escola
            ),


            "entradas": Entrada.objects.filter(
                escola=escola
            ),


            "calendario": CalendarioEscolar.objects.filter(
                escola=escola
            ),


            "trimestres": Trimestre.objects.filter(
                escola=escola
            ),


            "fechamento_notas": FechamentoNota.objects.filter(
                escola=escola
            ),


            "fechamento_trimestres": FechamentoTrimestre.objects.filter(
                escola=escola
            ),


            "mini_pautas": MiniPauta.objects.filter(
                escola=escola
            ),


            "notificacoes": Notificacao.objects.filter(
                escola=escola
            ),

        }


        for nome, queryset in modelos.items():


            ficheiro = (
                pasta
                /
                "dados"
                /
                f"{nome}.json"
            )


            with open(
                ficheiro,
                "w",
                encoding="utf-8"
            ) as f:


                json.dump(

                    json.loads(
                        serialize(
                            "json",
                            queryset
                        )
                    ),

                    f,

                    indent=4,

                    ensure_ascii=False

                )



    def exportar_info(
        self,
        escola,
        pasta
    ):


        info = {

            "sistema": "EdusCel",

            "escola": escola.nome,

            "codigo": escola.codigo,

            "data_backup": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),


            "usuarios": User.objects.filter(
                escola=escola
            ).count(),


            "alunos": Aluno.objects.filter(
                escola=escola
            ).count(),


            "professores": Professor.objects.filter(
                escola=escola
            ).count(),

        }


        with open(
            pasta / "info.json",
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                info,
                f,
                indent=4,
                ensure_ascii=False
            )



    def copiar_media(
        self,
        escola,
        pasta
    ):


        media_root = getattr(
            settings,
            "MEDIA_ROOT",
            None
        )


        if not media_root:
            return


        origem = Path(
            media_root
        )


        destino = (
            pasta
            /
            "media"
        )


        if origem.exists():

            shutil.copytree(

                origem,

                destino,

                dirs_exist_ok=True

            )



    def compactar_backup(
        self,
        escola,
        pasta
    ):


        nome = (
            escola.nome
            .replace(" ", "_")
        )


        arquivo = (
            self.base_backup
            /
            f"{nome}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.tar.gz"
        )


        with tarfile.open(
            arquivo,
            "w:gz"
        ) as tar:


            tar.add(
                pasta,
                arcname=pasta.name
            )


        return arquivo