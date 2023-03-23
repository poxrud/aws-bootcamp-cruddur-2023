import uuid
from datetime import datetime, timedelta, timezone

from lib.db import db


class CreateActivity:
  def run(message, user_handle, ttl):
    model = {
      'errors': None,
      'data': None
    }

    user_uuid = ""

    now = datetime.now(timezone.utc).astimezone()

    if (ttl == '30-days'):
      ttl_offset = timedelta(days=30)
    elif (ttl == '7-days'):
      ttl_offset = timedelta(days=7)
    elif (ttl == '3-days'):
      ttl_offset = timedelta(days=3)
    elif (ttl == '1-day'):
      ttl_offset = timedelta(days=1)
    elif (ttl == '12-hours'):
      ttl_offset = timedelta(hours=12)
    elif (ttl == '3-hours'):
      ttl_offset = timedelta(hours=3)
    elif (ttl == '1-hour'):
      ttl_offset = timedelta(hours=1)
    else:
      model['errors'] = ['ttl_blank']

    if user_handle == None or len(user_handle) < 1:
      model['errors'] = ['user_handle_blank']

    if message == None or len(message) < 1:
      model['errors'] = ['message_blank']
    elif len(message) > 280:
      model['errors'] = ['message_exceed_max_chars']

    if model['errors']:
      model['data'] = {
        'handle': user_handle,
        'message': message
      }
    else:
      self.create_activity()
      model['data'] = {
        'uuid': uuid.uuid4(),
        'display_name': 'Andrew Brown',
        'handle': user_handle,
        'message': message,
        'created_at': now.isoformat(),
        'expires_at': (now + ttl_offset).isoformat()
      }
    return model


def create_activity(handle, message, expires_at):
  sql = """
  insert into (
    user_uuid,
    message,
    expires_at
  )
  values (
    (select uuid from public.users where users.handle = %(handle)s limit 1), 
    %(user_uuid)s, 
    %(message)s, 
    %(expires_at)s) returning uuid;
  """
  uuid = db.query_commit_with_returning_id(sql, handle, message, expires_at)
