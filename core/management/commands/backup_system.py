import gzip
import os
import shutil
import subprocess
import tarfile

from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):

    help = "Executa o backup automático completo do sistema EdusCel."

    RETENTION_DAYS = 30


    def handle(self, *args, **options):

        self.stdout.write("")

        self.stdout.write("=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                "EDUSCEL - SISTEMA DE BACKUP"
            )
        )
        self.stdout.write("=" * 60)


        backup_root = (
            Path(settings.BASE_DIR)
            /
            "backups"
        )


        database_dir = backup_root / "database"

        media_dir = backup_root / "media"


        database_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        media_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )


        try:


            self.backup_database(
                database_dir,
                timestamp
            )


            self.backup_media(
                media_dir,
                timestamp
            )


            self.remove_old_backups(
                database_dir
            )


            self.remove_old_backups(
                media_dir
            )


            self.stdout.write("")


            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Backup concluído com sucesso."
                )
            )


        except Exception as e:

            raise CommandError(
                f"Erro durante o backup: {e}"
            )



    # ======================================================
    # DATABASE
    # ======================================================


    def backup_database(
        self,
        database_dir,
        timestamp
    ):


        engine = settings.DATABASES["default"]["ENGINE"]


        if "postgresql" in engine:


            self.backup_postgres(
                database_dir,
                timestamp
            )


            return



        elif "sqlite3" in engine:


            self.backup_sqlite(
                database_dir,
                timestamp
            )


            return



        else:

            raise Exception(
                "Banco de dados não suportado."
            )



    # ======================================================
    # POSTGRESQL
    # ======================================================


    def backup_postgres(
        self,
        database_dir,
        timestamp
    ):


        pg_dump = shutil.which(
            "pg_dump"
        )


        if pg_dump is None:

            raise Exception(
                "pg_dump não encontrado. Instale PostgreSQL Client."
            )



        db = settings.DATABASES["default"]



        arquivo_sql = (
            database_dir
            /
            f"eduscel_{timestamp}.sql"
        )


        arquivo_gzip = (
            database_dir
            /
            f"eduscel_{timestamp}.sql.gz"
        )



        env = os.environ.copy()

        env["PGPASSWORD"] = str(
            db["PASSWORD"]
        )



        comando = [

            pg_dump,

            "-h",
            db["HOST"] or "localhost",

            "-p",
            str(
                db["PORT"] or "5432"
            ),

            "-U",
            db["USER"],

            "-F",
            "p",

            db["NAME"]

        ]



        self.stdout.write(
            "• Criando backup PostgreSQL..."
        )



        with open(
            arquivo_sql,
            "wb"
        ) as output:


            subprocess.run(

                comando,

                stdout=output,

                stderr=subprocess.PIPE,

                env=env,

                check=True

            )



        with open(
            arquivo_sql,
            "rb"
        ) as origem:


            with gzip.open(
                arquivo_gzip,
                "wb"
            ) as destino:


                shutil.copyfileobj(
                    origem,
                    destino
                )



        arquivo_sql.unlink()



        self.stdout.write(

            self.style.SUCCESS(

                f"  ✓ {arquivo_gzip.name}"

            )

        )



    # ======================================================
    # SQLITE
    # ======================================================


    def backup_sqlite(
        self,
        database_dir,
        timestamp
    ):


        db_path = Path(
            settings.DATABASES["default"]["NAME"]
        )


        if not db_path.exists():

            raise Exception(
                "Banco SQLite não encontrado."
            )



        destino = (

            database_dir

            /

            f"eduscel_{timestamp}.sqlite3.gz"

        )



        self.stdout.write(
            "• Criando backup SQLite..."
        )



        with open(
            db_path,
            "rb"
        ) as origem:


            with gzip.open(
                destino,
                "wb"
            ) as arquivo:


                shutil.copyfileobj(
                    origem,
                    arquivo
                )



        self.stdout.write(

            self.style.SUCCESS(

                f"  ✓ {destino.name}"

            )

        )



    # ======================================================
    # MEDIA
    # ======================================================


    def backup_media(
        self,
        media_dir,
        timestamp
    ):


        media_root = Path(
            settings.MEDIA_ROOT
        )


        if not media_root.exists():

            self.stdout.write(

                self.style.WARNING(

                    "MEDIA_ROOT não encontrada."

                )

            )

            return



        arquivo = (

            media_dir

            /

            f"media_{timestamp}.tar.gz"

        )



        self.stdout.write(
            "• Criando backup MEDIA..."
        )



        with tarfile.open(
            arquivo,
            "w:gz"
        ) as tar:


            tar.add(

                media_root,

                arcname="media"

            )



        self.stdout.write(

            self.style.SUCCESS(

                f"  ✓ {arquivo.name}"

            )

        )



    # ======================================================
    # RETENÇÃO
    # ======================================================


    def remove_old_backups(
        self,
        directory
    ):


        limite = (

            datetime.now()

            -

            timedelta(
                days=self.RETENTION_DAYS
            )

        )


        for file in directory.iterdir():


            if not file.is_file():

                continue



            data = datetime.fromtimestamp(

                file.stat().st_mtime

            )



            if data < limite:


                file.unlink()


                self.stdout.write(

                    self.style.WARNING(

                        f"  • Removido: {file.name}"

                    )

                )