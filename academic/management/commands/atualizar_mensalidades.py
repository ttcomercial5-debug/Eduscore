from django.core.management.base import BaseCommand
from django.utils import timezone
from academic.models import Mensalidade

class Command(BaseCommand):
    help = "Atualiza status das mensalidades vencidas"

    def handle(self, *args, **kwargs):
        hoje = timezone.now().date()

        mensalidades = Mensalidade.objects.filter(
            vencimento__lt=hoje,
            status__in=["PENDENTE", "PARCIAL"]
        ).select_related("aluno")

        total = 0
        for m in mensalidades:
            m.atualizar_status()
            total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{total} mensalidades atualizadas."
            )
        )