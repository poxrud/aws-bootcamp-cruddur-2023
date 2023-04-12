import os
import requests
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
        raise TokenVerifyError("unathenticated")

      data = response.json()

      return data
    except Exception as e:
      raise e
