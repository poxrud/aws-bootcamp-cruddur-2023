from datetime import datetime, timedelta, timezone
from utils.logger import LOGGER

from lib.db import db

from opentelemetry import trace

tracer = trace.get_tracer("home-activities")


class HomeActivities:
  def run(cognito_user_id=None):
    LOGGER.info("HomeActivities")

    with tracer.start_as_current_span("home-activities-mock-data"):
      now = datetime.now(timezone.utc).astimezone()
      span = trace.get_current_span()
      span.set_attribute("app.userId", 1001)
      span.set_attribute("app.now", now.isoformat())

      sql = db.template('activities', 'home')
      results = db.query_array_json(sql)
      return results
