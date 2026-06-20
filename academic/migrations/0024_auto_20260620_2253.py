from django.db import migrations


def criar_planos(apps, schema_editor):

    Plano = apps.get_model('academic', 'Plano')

    Plano.objects.get_or_create(
        nome="Básico",
        defaults={
            "limite_alunos": 300,
            "valor_mensal": 25000,
            "ativo": True,
        },
    )

    Plano.objects.get_or_create(
        nome="Profissional",
        defaults={
            "limite_alunos": 800,
            "valor_mensal": 60000,
            "ativo": True,
        },
    )

    Plano.objects.get_or_create(
        nome="Premium",
        defaults={
            "limite_alunos": 999999,
            "valor_mensal": 120000,
            "ativo": True,
        },
    )


def remover_planos(apps, schema_editor):

    Plano = apps.get_model('academic', 'Plano')
    Plano.objects.filter(nome__in=["Básico", "Profissional", "Premium"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0023_remove_plano_data_expiracao_remove_plano_escola_and_more'),  # mantém o teu número real aqui
    ]

    operations = [
        migrations.RunPython(criar_planos, remover_planos),
    ]