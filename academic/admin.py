from django.contrib import admin
from .models import (
    Escola,
    Turma,
    Disciplina,
    Aluno,
    Nota,
    Frequencia,
    Tarefa
)

admin.site.register(Escola)
admin.site.register(Turma)
admin.site.register(Disciplina)
admin.site.register(Aluno)
admin.site.register(Nota)
admin.site.register(Frequencia)
admin.site.register(Tarefa)