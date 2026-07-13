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
    help = "Executa o backup automático do sistema EdusCel."

    RETENTION_DAYS = 30

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("EDUSCEL - SISTEMA DE BACKUP"))
        self.stdout.write("=" * 60)

        backup_root = Path(settings.BASE_DIR) / "backups"
        postgres_dir = backup_root / "postgres"
        media_dir = backup_root / "media"

        postgres_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            self.backup_database(postgres_dir, timestamp)
            self.backup_media(media_dir, timestamp)
            self.remove_old_backups(postgres_dir)
            self.remove_old_backups(media_dir)

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS("✓ Backup concluído com sucesso.")
            )

        except Exception as e:
            raise CommandError(f"Erro durante o backup: {e}")

    # ==========================================================
    # BACKUP DO POSTGRESQL
    # ==========================================================

    def backup_database(self, postgres_dir: Path, timestamp: str):

        engine = settings.DATABASES["default"]["ENGINE"]

        if "postgresql" not in engine:
            self.stdout.write(
                self.style.WARNING(
                    "SQLite detectado. Backup da base de dados ignorado."
                )
            )
            return

        if shutil.which("pg_dump") is None:
            raise CommandError(
                "pg_dump não foi encontrado no servidor."
            )

        db = settings.DATABASES["default"]

        sql_file = postgres_dir / f"eduscel_{timestamp}.sql"
        gzip_file = postgres_dir / f"eduscel_{timestamp}.sql.gz"

        env = os.environ.copy()
        env["PGPASSWORD"] = db["PASSWORD"]

        command = [
            "pg_dump",
            "-h",
            db["HOST"] or "localhost",
            "-p",
            str(db["PORT"] or "5432"),
            "-U",
            db["USER"],
            "-F",
            "p",
            db["NAME"],
        ]

        self.stdout.write("• Criando backup do PostgreSQL...")

        with open(sql_file, "wb") as output:
            subprocess.run(
                command,
                stdout=output,
                stderr=subprocess.PIPE,
                env=env,
                check=True,
            )

        with open(sql_file, "rb") as src:
            with gzip.open(gzip_file, "wb") as dst:
                shutil.copyfileobj(src, dst)

        sql_file.unlink()

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {gzip_file.name}"
            )
        )

    # ==========================================================
    # BACKUP DA MEDIA
    # ==========================================================

    def backup_media(self, media_dir: Path, timestamp: str):

        media_root = Path(settings.MEDIA_ROOT)

        if not media_root.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Pasta MEDIA_ROOT não encontrada."
                )
            )
            return

        backup_file = media_dir / f"media_{timestamp}.tar.gz"

        self.stdout.write("• Criando backup da pasta media...")

        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(media_root, arcname="media")

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {backup_file.name}"
            )
        )

    # ==========================================================
    # LIMPEZA DOS BACKUPS
    # ==========================================================

    def remove_old_backups(self, directory: Path):

        limite = datetime.now() - timedelta(days=self.RETENTION_DAYS)

        for file in directory.iterdir():

            if not file.is_file():
                continue

            modified = datetime.fromtimestamp(file.stat().st_mtime)

            if modified < limite:
                file.unlink()

                self.stdout.write(
                    self.style.WARNING(
                        f"  • Removido: {file.name}"
                    )
                )