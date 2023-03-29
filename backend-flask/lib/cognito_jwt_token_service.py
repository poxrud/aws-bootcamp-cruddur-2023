
import requests

class CognitoJwtToken:
  def verify(auth_header):
    try:
      response = requests.get('http://verify-cognito-token:3050/verify-cognito-token', headers={'Authorization': f'{auth_header}'})
      data = response.json()
      return data
    except:
      raise "Cannot Access JWT Verification Service"