from flask import got_request_exception
import rollbar.contrib.flask
import rollbar
from utils.logger import LOGGER
from time import strftime
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry import trace
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin
import os

from lib.cognito_jwt_token_service import CognitoJwtToken, TokenVerifyError

from services.users_short import *
from services.home_activities import *
from services.notifications_activities import *
from services.user_activities import *
from services.create_activity import *
from services.create_reply import *
from services.search_activities import *
from services.message_groups import *
from services.messages import *
from services.create_message import *
from services.show_activity import *
from services.update_profile import *

# AWS X-RAY --------------
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
xray_url = os.getenv("AWS_XRAY_URL")
xray_recorder.configure(service='backend-flask', dynamic_naming=xray_url)

# Honeycomb --------------

# Initialize tracing and an exporter that can send data to Honeycomb
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# CloudWatch Logs ------------


# Rollbar -----------------

app = Flask(__name__)

# AWS X-RAY -------------
XRayMiddleware(app, xray_recorder)

# Honeycomb -------------
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

frontend = os.getenv('FRONTEND_URL')
backend = os.getenv('BACKEND_URL')
origins = [frontend, backend]
cors = CORS(
  app,
  resources={r"/api/*": {"origins": origins}},
  expose_headers="location,link",
  allow_headers=["content-type", "if-modified-since",
                 "traceparent", "Authorization"],
  methods="OPTIONS,GET,HEAD,POST"
)


@app.route("/api/message_groups", methods=['GET'])
def data_message_groups():
  cognito_user_id = None
  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("token not provided")
    return {}, 401
  try:
    data = CognitoJwtToken.verify(auth_header)
    cognito_user_id = data['sub']

    model = MessageGroups.run(cognito_user_id=cognito_user_id)

    if model['errors'] is not None:
      return model['errors'], 422
    else:
      return model['data'], 200

  except TokenVerifyError as e:
    LOGGER.info("unverified")
    return {}, 401


@app.route("/api/messages/<string:message_group_uuid>", methods=['GET'])
def data_messages(message_group_uuid):

  cognito_user_id = None
  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("token not provided")
    return {}, 401
  try:
    data = CognitoJwtToken.verify(auth_header)
    cognito_user_id = data['sub']

    model = Messages.run(cognito_user_id=cognito_user_id,
                         message_group_uuid=message_group_uuid)

    if model['errors'] is not None:
      return model['errors'], 422
    else:
      return model['data'], 200

  except TokenVerifyError as e:
    LOGGER.info("unverified")
    return {}, 401


@app.route("/api/messages", methods=['POST', 'OPTIONS'])
@cross_origin()
def data_create_message():
  message_group_uuid = request.json.get('message_group_uuid', None)
  user_receiver_handle = request.json.get('handle', None)
  message = request.json['message']
  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("token not provided")
    return {}, 401

  try:
    data = CognitoJwtToken.verify(auth_header)
    # authenicatied request
    app.logger.debug("authenicated")
    app.logger.debug(data)

    cognito_user_id = data['sub']

    if message_group_uuid == None:
      # Create for the first time
      model = CreateMessage.run(
        mode="create",
        message=message,
        cognito_user_id=cognito_user_id,
        user_receiver_handle=user_receiver_handle
      )
    else:
      # Push onto existing Message Group
      LOGGER.debug("Message:")
      LOGGER.debug(message)
      LOGGER.debug("GROUP UUID:")
      LOGGER.debug(message_group_uuid)
      LOGGER.debug("COGNITO UUID:")
      LOGGER.debug(cognito_user_id)

      model = CreateMessage.run(
        mode="update",
        message=message,
        message_group_uuid=message_group_uuid,
        cognito_user_id=cognito_user_id
      )
    if model['errors'] is not None:
      return model['errors'], 422
    else:
      return model['data'], 200
  except TokenVerifyError as e:
    # unauthenicatied request
    app.logger.debug(e)
    return {}, 401


@app.route("/api/activities/home", methods=['GET'])
def data_home():
  cognito_user_id = None
  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("token not provided")
    data = HomeActivities.run()
    return data, 200

  try:
    data = CognitoJwtToken.verify(auth_header)
    cognito_user_id = data['username']
    data = HomeActivities.run(cognito_user_id)
  except TokenVerifyError as e:
    LOGGER.info("unauthenticated")
    data = HomeActivities.run()

  return data, 200


@app.route("/api/activities/notifications", methods=['GET'])
def data_notifications():
  data = NotificationsActivities.run()
  return data, 200


@app.route("/api/activities/@<string:handle>", methods=['GET'])
def data_handle(handle):
  model = UserActivities.run(handle)
  if model['errors'] is not None:
    return model['errors'], 422
  else:
    return model['data'], 200


@app.route("/api/activities/search", methods=['GET'])
def data_search():
  term = request.args.get('term')
  model = SearchActivities.run(term)
  if model['errors'] is not None:
    return model['errors'], 422
  else:
    return model['data'], 200
  return


@app.route("/api/activities", methods=['POST', 'OPTIONS'])
@cross_origin()
def data_activities():
  user_handle = 'philoxrud'
  message = request.json['message']
  ttl = request.json['ttl']
  model = CreateActivity.run(message, user_handle, ttl)
  if model['errors'] is not None:
    return model['errors'], 422
  else:
    return model['data'], 200
  return


@app.route("/api/activities/<string:activity_uuid>", methods=['GET'])
def data_show_activity(activity_uuid):
  data = ShowActivity.run(activity_uuid=activity_uuid)
  return data, 200


@app.route("/api/activities/<string:activity_uuid>/reply", methods=['POST', 'OPTIONS'])
@cross_origin()
def data_activities_reply(activity_uuid):
  user_handle = 'andrewbrown'
  message = request.json['message']
  model = CreateReply.run(message, user_handle, activity_uuid)
  if model['errors'] is not None:
    return model['errors'], 422
  else:
    return model['data'], 200
  return


@app.route("/api/users/@<string:handle>/short", methods=['GET'])
def data_users_short(handle):
  data = UsersShort.run(handle)
  return data, 200


@app.route("/api/profile/update", methods=['POST', 'OPTIONS'])
@cross_origin()
def data_update_profile():

  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("auth token not provided")
    return {}, 401

  bio = request.json.get('bio', None)
  display_name = request.json.get('display_name', None)

  try:
    claims = CognitoJwtToken.verify(auth_header)
    cognito_user_id = claims['sub']
    model = UpdateProfile.run(
      cognito_user_id=cognito_user_id,
      bio=bio,
      display_name=display_name
    )
    if model['errors'] is not None:
      return model['errors'], 422
    else:
      return model['data'], 200
  except TokenVerifyError as e:
    # unauthenicatied request
    LOGGER.debug(e)
    return {}, 401


rollbar_access_token = os.getenv('ROLLBAR_ACCESS_TOKEN')

# @app.before_first_request


def init_rollbar():
  """init rollbar module"""
  rollbar.init(
      # access token
      rollbar_access_token,
      # environment name
      'production',
      # server root directory, makes tracebacks prettier
      root=os.path.dirname(os.path.realpath(__file__)),
      # flask already sets up logging
      allow_logging_basic_config=False)

  # send exceptions from `app` to rollbar, using flask's signal system.
  got_request_exception.connect(rollbar.contrib.flask.report_exception, app)


init_rollbar()


@app.after_request
def after_request(response):
  timestamp = strftime('[%Y-%b-%d %H:%M]')
  LOGGER.error('%s %s %s %s %s %s', timestamp, request.remote_addr,
               request.method, request.scheme, request.full_path, response.status)
  return response


@app.route('/api/health-check')
def health_check():
  return {'success': True, 'version': 2}, 200


# Rollbar test path ------------
# @app.route('/rollbar/test')
# def rollbar_test():
#   rollbar.report_message('Hello World!', 'warning')
#   return "Hello World!"


if __name__ == "__main__":
  app.run(debug=True)
