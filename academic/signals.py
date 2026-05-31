from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Escola
from django.utils.crypto import get_random_string
from django.contrib import messages
import random
import string



User = get_user_model()

def gerar_senha(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))


@receiver(post_save, sender=Escola)
def criar_diretor_automatico(sender, instance, created, **kwargs):

    if created:

        User = get_user_model()

        senha = gerar_senha()
        username_diretor = f"diretor_{instance.id}"

        User.objects.create_user(
            username=username_diretor,
            password=senha,
            role='DIRETOR',
            escola=instance
        )

        print("=================================")
        print("ESCOLA CRIADA COM SUCESSO")
        print(f"Username Diretor: {username_diretor}")
        print(f"Senha: {senha}")
        print("=================================")



from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Escola
from .models import AnoLetivo
from .models import gerar_ano_automatico


@receiver(post_save, sender=Escola)
def criar_ano_automatico(sender, instance, created, **kwargs):

    if created:

        AnoLetivo.objects.get_or_create(

            escola=instance,

            nome=gerar_ano_automatico(),

            defaults={
                "ativo": True
            }
        )