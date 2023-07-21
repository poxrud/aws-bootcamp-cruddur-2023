from flask import Flask, request, g
from flask_cors import cross_origin
from utils.logger import LOGGER

from lib.helpers import model_json
from lib.cognito_jwt_token_service import jwt_required

from services.message_groups import MessageGroups
from services.messages import Messages
from services.create_message import CreateMessage


def load(app):

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
