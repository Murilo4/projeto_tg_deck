import jwt
import os
from datetime import datetime, timezone
from django.core.cache import cache
import hashlib
SECRET_KEY = os.getenv('SECRET_KEY')


def blacklist_jwt(token):
    # Calcular o tempo restante de expiração
    try:
        decoded_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
        exp_timestamp = decoded_data.get("exp")
        exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
        time_to_expire = (exp_datetime - datetime.now(timezone.utc)).total_seconds()
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache.set(f'blacklisted_token_{token_hash}', True, timeout=int(time_to_expire))
    except jwt.InvalidTokenError:
        pass


def is_token_blacklisted(token):
    token_hash = hashlib.md5(token.encode()).hexdigest()
    return cache.get(f'blacklisted_token_{token_hash}') is not None


def validate_jwt(token):
    if is_token_blacklisted(token):
        return {"error": "Token já foi revogado."}
    try:
        decoded_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded_data
    except jwt.ExpiredSignatureError:
        return {"error": "Token expirado."}
    except jwt.InvalidTokenError:
        return {"error": "Token inválido."}
