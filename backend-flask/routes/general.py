from flask import request
from time import strftime
from utils.logger import LOGGER


def load(app):
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
