from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'ADMIN'


class IsProfessor(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'PROFESSOR'


class IsAluno(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'ALUNO'


class IsPai(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'PAI'