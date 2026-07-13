"""
Serviço SMS do EdusCel.

Fornecedor:
- KambasSMS

Responsável por:
- Enviar OTP de recuperação de senha.
- Futuramente enviar notificações SMS do sistema.

A view nunca chama diretamente a API.
Toda comunicação passa por este serviço.
"""


import requests

from django.conf import settings





def enviar_sms(telefone, mensagem):

    """
    Envia SMS através do KambasSMS.

    Args:
        telefone:
            Número do destinatário.

        mensagem:
            Texto da mensagem.

    Returns:
        True:
            SMS enviado com sucesso.

        False:
            Falha no envio.
    """



    # ======================================
    # CONFIGURAÇÃO KAMBAS SMS
    # ======================================

    url = getattr(
        settings,
        "KAMBAS_SMS_URL",
        None
    )


    token = getattr(
        settings,
        "KAMBAS_SMS_TOKEN",
        None
    )


    remetente = getattr(
        settings,
        "KAMBAS_SMS_SENDER",
        "EdusCel"
    )




    # ======================================
    # MODO DESENVOLVIMENTO
    # Caso ainda não exista API configurada
    # ======================================

    if not url or not token:


        print("\n")
        print("=" * 60)
        print("EDUSCEL - SMS TESTE")
        print("=" * 60)

        print(
            f"Telefone: {telefone}"
        )

        print(
            "\nMensagem:"
        )

        print(
            mensagem
        )

        print("=" * 60)
        print("\n")


        return True





    # ======================================
    # ENVIO REAL KAMBAS SMS
    # ======================================


    headers = {

        "Authorization":
        f"Bearer {token}",


        "Content-Type":
        "application/json"

    }




    payload = {


        "sender":

        remetente,


        "to":

        telefone,


        "message":

        mensagem

    }




    try:


        response = requests.post(

            url,

            json=payload,

            headers=headers,

            timeout=10

        )



        if response.status_code in [200, 201]:


            return True




        print(
            "Erro KambasSMS:"
        )


        print(
            response.text
        )


        return False





    except requests.exceptions.RequestException as erro:


        print(
            "Falha na conexão KambasSMS:"
        )


        print(
            erro
        )


        return False