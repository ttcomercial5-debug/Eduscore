from django.db import models
from django.utils import timezone
from academic.models import Aluno, Escola


# ==========================================================
# PAGAMENTO DE ALUNO (Mensalidade Escolar)
# ==========================================================






from django.db import models
from django.conf import settings



class MovimentoCaixa(models.Model):

    TIPOS = (
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
    )

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    tipo = models.CharField(max_length=10, choices=TIPOS)

    descricao = models.CharField(max_length=255)

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data = models.DateTimeField(auto_now_add=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    origem = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.valor}"


