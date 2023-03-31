
import requests
from utils.logger import LOGGER


class TokenVerifyError(Exception):
  pass


class CognitoJwtToken:
  def verify(auth_header):
    try:

      response = requests.get('http://verify-cognito-token:3050/verify-cognito-token',
                              headers={'Authorization': f'{auth_header}'})

      LOGGER.debug("AUTHHEADER:")
      LOGGER.debug(response.status_code)

      if response.status_code == 401:
        raise TokenVerifyError("unathenticated")

      data = response.json()

      return data
    except Exception as e:
      raise e
