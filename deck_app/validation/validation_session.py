import requests
from django.core.exceptions import ValidationError


def validate_session():
    response = requests.post(
        'https://projeto-tg-back-end.onrender.com/validate-token-in-session/')
    if response.status_code == 404:
        raise ValidationError('Não foi possivel validar o token.')
    # elif response.status_code == 401:
    #     raise ValidationError("Sessão invalida")
