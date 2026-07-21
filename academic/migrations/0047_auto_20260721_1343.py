from django.db import migrations

from django.db import migrations


def migrar_formas_pagamento(apps, schema_editor):

    Pagamento = apps.get_model(
        "academic",
        "Pagamento"
    )

    MetodoPagamento = apps.get_model(
        "academic",
        "MetodoPagamento"
    )

    Escola = apps.get_model(
        "academic",
        "Escola"
    )


    mapa = {

        "DINHEIRO": "Dinheiro",

        "TRANSFERENCIA": "Transferência",

        "TPA": "TPA",

        "MULTICAIXA": "Multicaixa",

        "OUTRO": "Outro",

    }



    for pagamento in Pagamento.objects.all():


        codigo_antigo = pagamento.forma_pagamento



        if not codigo_antigo:
            continue



        escola = pagamento.escola



        metodo, criado = MetodoPagamento.objects.get_or_create(

            escola=escola,

            codigo=codigo_antigo,

            defaults={

                "nome": mapa.get(
                    codigo_antigo,
                    codigo_antigo
                ),

                "ativo": True,

            }

        )



        pagamento.forma_pagamento = metodo

        pagamento.save(
            update_fields=[
                "forma_pagamento"
            ]
        )




class Migration(migrations.Migration):


    dependencies = [

        (
            'academic', '0046_alter_pagamento_forma_pagamento'
        ),

    ]


    operations = [


        migrations.RunPython(
            migrar_formas_pagamento
        ),


    ]



