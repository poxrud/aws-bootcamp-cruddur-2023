import os
import requests
from functools import wraps, partial
from flask import request, g
from utils.logger import LOGGER


class TokenVerifyError(Exception):
  pass


class CognitoJwtToken:
  def verify(auth_header):
    try:
      jwt_verifier_path = os.getenv('JWT_VERIFIER_SIDECAR_URL')
      response = requests.get(f'{jwt_verifier_path}/verify-cognito-token',
                              headers={'Authorization': f'{auth_header}'})

      if response.status_code == 401:
        raise TokenVerifyError("unauthenticated")

      data = response.json()

      return data
    except Exception as e:
      raise e


def jwt_required(f=None, on_error=None):
  if f is None:
    return partial(jwt_required, on_error=on_error)

  @wraps(f)
  def decorated_function(*args, **kwargs):
    auth_header = request.headers.get('Authorization')
    if (auth_header == None):
      if on_error:
        return on_error("token not provided")

      LOGGER.debug("token not provided")
      return {}, 401

    try:
      claims = CognitoJwtToken.verify(auth_header)
      g.cognito_user_id = claims['sub']
    except TokenVerifyError as e:
      # unauthenticated request
      LOGGER.debug(e)
      if on_error:
        return on_error(e)
      return {}, 401
    return f(*args, **kwargs)
  return decorated_function
