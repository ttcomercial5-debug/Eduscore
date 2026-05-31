from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Turma, Disciplina, Aluno, Nota, Frequencia, Tarefa
from .serializers import *
from .permissions import IsAdmin
from .models import Nota
from .serializers import NotaSerializer
from rest_framework.exceptions import PermissionDenied
from .models import Frequencia
from .serializers import FrequenciaSerializer


class TurmaViewSet(viewsets.ModelViewSet):
    queryset = Turma.objects.all()
    serializer_class = TurmaSerializer
    permission_classes = [IsAuthenticated]


class DisciplinaViewSet(viewsets.ModelViewSet):
    queryset = Disciplina.objects.all()
    serializer_class = DisciplinaSerializer
    permission_classes = [IsAuthenticated]


class AlunoViewSet(viewsets.ModelViewSet):
    queryset = Aluno.objects.all()
    serializer_class = AlunoSerializer
    permission_classes = [IsAuthenticated]





class NotaViewSet(viewsets.ModelViewSet):
    queryset = Nota.objects.all()
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        print("Usuário logado:", user)
        print("Role:", user.role)
        print("Escola:", user.escola)

        if user.role == 'SUPERADMIN':
            return Nota.objects.all()

        if user.escola:
            return Nota.objects.filter(escola=user.escola)

        return Nota.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        # Apenas ADMIN e PROFESSOR podem criar nota
        if user.role not in ['ADMIN', 'PROFESSOR']:
            raise PermissionDenied("Você não tem permissão para criar notas.")

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        if user.role not in ['ADMIN', 'PROFESSOR']:
            raise PermissionDenied("Você não tem permissão para editar notas.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if user.role != 'ADMIN':
            raise PermissionDenied("Apenas ADMIN pode apagar notas.")

        instance.delete()

class TarefaViewSet(viewsets.ModelViewSet):
    queryset = Tarefa.objects.all()
    serializer_class = TarefaSerializer
    permission_classes = [IsAuthenticated]


class FrequenciaViewSet(viewsets.ModelViewSet):
    queryset = Frequencia.objects.all()
    serializer_class = FrequenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ADMIN vê tudo
        if user.role == 'ADMIN':
            return Frequencia.objects.all()

        # PROFESSOR vê apenas frequência das disciplinas dele
        if user.role == 'PROFESSOR':
            return Frequencia.objects.filter(
                disciplina__professor=user
            )

        # ALUNO vê apenas sua própria frequência
        if user.role == 'ALUNO':
            return Frequencia.objects.filter(
                aluno__usuario=user
            )

        return Frequencia.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role not in ['ADMIN', 'PROFESSOR']:
            raise PermissionDenied("Você não tem permissão para registrar frequência.")

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        if user.role not in ['ADMIN', 'PROFESSOR']:
            raise PermissionDenied("Você não tem permissão para editar frequência.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if user.role != 'ADMIN':
            raise PermissionDenied("Apenas ADMIN pode apagar frequência.")

        instance.delete()


class TurmaViewSet(viewsets.ModelViewSet):
    queryset = Turma.objects.all()
    serializer_class = TurmaSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

from django.shortcuts import render

# Create your views here.
