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
from flask import Flask, request, g
from flask_cors import CORS, cross_origin
import os

from lib.cognito_jwt_token_service import jwt_required, CognitoJwtToken, TokenVerifyError

from lib.helpers import model_json

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
  expose_headers=["Authorization", "location", "link"],
  allow_headers=["content-type", "if-modified-since",
                 "traceparent", "Authorization"],
  methods="OPTIONS,GET,HEAD,POST"
)


@app.route("/api/message_groups", methods=['GET'])
@jwt_required()
def data_message_groups():
  model = MessageGroups.run(cognito_user_id=g.cognito_user_id)

  return model_json(model)


@app.route("/api/messages/<string:message_group_uuid>", methods=['GET'])
@jwt_required()
def data_messages(message_group_uuid):
  model = Messages.run(cognito_user_id=g.cognito_user_id,
                       message_group_uuid=message_group_uuid)

  return model_json(model)


@app.route("/api/messages", methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def data_create_message():
  message_group_uuid = request.json.get('message_group_uuid', None)
  user_receiver_handle = request.json.get('handle', None)
  message = request.json['message']

  # authenticated request
  LOGGER.debug("authenticated")
  LOGGER.debug(data)

  if message_group_uuid == None:
    # Create for the first time
    model = CreateMessage.run(
      mode="create",
      message=message,
      cognito_user_id=g.cognito_user_id,
      user_receiver_handle=user_receiver_handle
    )
  else:
    # Push onto existing Message Group
    # LOGGER.debug("Message:")
    # LOGGER.debug(message)
    # LOGGER.debug("GROUP UUID:")
    # LOGGER.debug(message_group_uuid)
    # LOGGER.debug("COGNITO UUID:")
    # LOGGER.debug(g.cognito_user_id)

    model = CreateMessage.run(
      mode="update",
      message=message,
      message_group_uuid=message_group_uuid,
      cognito_user_id=g.cognito_user_id
    )

  return model_json(model)


def default_home_feed(e):
  LOGGER.debug(e)
  data = HomeActivities.run()
  return data, 200


@app.route("/api/activities/home", methods=['GET'])
@jwt_required(on_error=default_home_feed)
def data_home():
  data = HomeActivities.run(cognito_user_id=g.cognito_user_id)
  return data, 200


@app.route("/api/activities/notifications", methods=['GET'])
def data_notifications():
  data = NotificationsActivities.run()
  return data, 200


@app.route("/api/activities/@<string:handle>", methods=['GET'])
def data_handle(handle):
  model = UserActivities.run(handle)
  return model_json(model)


@app.route("/api/activities/search", methods=['GET'])
def data_search():
  term = request.args.get('term')
  model = SearchActivities.run(term)
  return model_json(model)


@app.route("/api/activities", methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def data_activities():
  LOGGER.debug("authenticated")
  LOGGER.debug(data)

  message = request.json['message']
  ttl = request.json['ttl']
  model = CreateActivity.run(message, g.cognito_user_id, ttl)

  return model_json(model)


@app.route("/api/activities/<string:activity_uuid>", methods=['GET'])
def data_show_activity(activity_uuid):
  data = ShowActivity.run(activity_uuid=activity_uuid)
  return data, 200


@app.route("/api/activities/<string:activity_uuid>/reply", methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def data_activities_reply(activity_uuid):
  message = request.json['message']
  model = CreateReply.run(message, g.cognito_user_id, activity_uuid)
  return model_json(model)


@app.route("/api/users/@<string:handle>/short", methods=['GET'])
def data_users_short(handle):
  data = UsersShort.run(handle)
  return data, 200


@app.route("/api/profile/update", methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def data_update_profile():
  bio = request.json.get('bio', None)
  display_name = request.json.get('display_name', None)

  model = UpdateProfile.run(
    cognito_user_id=g.cognito_user_id,
    bio=bio,
    display_name=display_name
  )
  return model_json(model)


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
