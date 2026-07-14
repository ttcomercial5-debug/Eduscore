"""
Serviço SMS do EdusCel.

Fornecedor:
- Infobip

Responsável por:
- Enviar OTP de recuperação de senha.
- Futuramente enviar notificações SMS do sistema.

Todas as views do sistema devem utilizar apenas a função
enviar_sms(), sem comunicar diretamente com a API.
"""

import requests

from django.conf import settings


def enviar_sms(telefone, mensagem):
    """
    Envia SMS através da Infobip.

    Args:
        telefone (str):
            Número do destinatário.

        mensagem (str):
            Texto da mensagem.

    Returns:
        bool:
            True se enviado com sucesso.
            False caso ocorra algum erro.
    """

    # =====================================
    # CONFIGURAÇÕES
    # =====================================

    api_key = getattr(
        settings,
        "INFOBIP_API_KEY",
        None
    )

    base_url = getattr(
        settings,
        "INFOBIP_BASE_URL",
        None
    )

    remetente = getattr(
        settings,
        "INFOBIP_SENDER",
        "EdusCel"
    )

    # =====================================
    # MODO TESTE
    # =====================================

    if not api_key or not base_url:

        print("\n")
        print("=" * 60)
        print("EDUSCEL - SMS (MODO TESTE)")
        print("=" * 60)
        print(f"Telefone : {telefone}")
        print(f"Mensagem : {mensagem}")
        print("=" * 60)
        print("\n")

        return True

    # =====================================
    # FORMATA O TELEFONE
    # =====================================

    telefone = telefone.replace("+", "").replace(" ", "")

    if telefone.startswith("0"):
        telefone = telefone[1:]

    if not telefone.startswith("244"):
        telefone = "244" + telefone

    # =====================================
    # ENDPOINT
    # =====================================

    url = f"https://{base_url}/sms/2/text/advanced"

    # =====================================
    # CABEÇALHOS
    # =====================================

    headers = {
        "Authorization": f"App {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # =====================================
    # PAYLOAD
    # =====================================

    payload = {
        "messages": [
            {
                "from": remetente,
                "destinations": [
                    {
                        "to": telefone
                    }
                ],
                "text": mensagem
            }
        ]
    }

    # =====================================
    # ENVIO
    # =====================================

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code in [200, 201]:

            try:

                resposta = response.json()

                print("\n===== INFOBIP =====")
                print(resposta)
                print("===================\n")

                return True

            except Exception:

                print(response.text)

                return True

        print(
            f"Erro HTTP: {response.status_code}"
        )

        print(response.text)

        return False

    except requests.exceptions.RequestException as erro:

        print(
            "Falha ao comunicar com a Infobip:"
        )

        print(erro)

        return False