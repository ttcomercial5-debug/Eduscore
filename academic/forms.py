from django import forms
from .models import Disciplina, Configuracao



class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = '__all__'
        widgets = {
            'mensagem_manutencao': forms.Textarea(attrs={'rows':3}),
            'cor_principal': forms.TextInput(attrs={'type':'color'}),
            'cor_secundaria': forms.TextInput(attrs={'type':'color'}),
        }


class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = [
            'nome',
            'turma',
            'professor'
]



from .models import Aluno, Curso

# ===============================
# Formulário Aluno
# ===============================
class AlunoForm(forms.ModelForm):
    # Aceita datas no formato dd/mm/aaaa
    data_nascimento = forms.DateField(
        required=True,
        input_formats=['%d/%m/%Y', '%Y-%m-%d'],  # aceita ambos
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Aluno
        fields = "__all__"  # Corrigido

    def __init__(self, *args, **kwargs):
        escola = kwargs.pop("escola", None)
        super().__init__(*args, **kwargs)

        # Filtrar cursos pela escola
        if escola:
            self.fields["curso"].queryset = Curso.objects.filter(escola=escola)

        # Adicionar placeholder para o nome do aluno
        self.fields["usuario"].widget.attrs.update({
            "placeholder": "Nome completo do aluno"
        })
        self.fields["numero_bi"].widget.attrs.update({
            "placeholder": "Número do BI"
        })
        self.fields["numero_processo"].widget.attrs.update({
            "placeholder": "Número do processo"
        })



from django import forms
from .models import CalendarioEscolar

# ==========================================================
# FORM CALENDÁRIO ESCOLAR
# ==========================================================

class CalendarioEscolarForm(forms.ModelForm):

    class Meta:

        model = CalendarioEscolar

        fields = [

            "titulo",
            "descricao",
            "tipo",
            "prioridade",
            "turma",
            "evento_geral",

            "data_inicio",
            "data_fim",

            "hora_inicio",
            "hora_fim",

            "mostrar_para_diretor",
            "mostrar_para_professor",
            "mostrar_para_aluno",
            "mostrar_para_secretaria",

            "enviar_notificacao",

        ]

        widgets = {

            # =========================================
            # TEXTO
            # =========================================

            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o título do evento"
                }
            ),

            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Descrição do evento"
                }
            ),

            # =========================================
            # SELECT
            # =========================================

            "tipo": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "prioridade": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "turma": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            # =========================================
            # DATAS
            # =========================================

            "data_inicio": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "data_fim": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            # =========================================
            # HORAS
            # =========================================

            "hora_inicio": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time"
                }
            ),

            "hora_fim": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time"
                }
            ),

            # =========================================
            # CHECKBOX
            # =========================================

            "evento_geral": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "mostrar_para_diretor": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "mostrar_para_professor": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "mostrar_para_aluno": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "mostrar_para_secretaria": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "enviar_notificacao": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

        }

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["turma"].required = False
        self.fields["data_fim"].required = False
        self.fields["hora_inicio"].required = False
        self.fields["hora_fim"].required = False