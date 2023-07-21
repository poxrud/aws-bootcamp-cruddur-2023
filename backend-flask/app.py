from flask import Flask
from utils.logger import LOGGER

from lib.rollbar import init_rollbar
from lib.xray import init_xray
from lib.honeycomb import init_honeycomb
from lib.cors import init_cors

import routes.activities
import routes.users
import routes.messages
import routes.general

app = Flask(__name__)
init_rollbar(app)
init_xray(app)
init_honeycomb(app)
init_cors(app)

routes.activities.load(app)
routes.users.load(app)
routes.messages.load(app)
routes.general.load(app)

if __name__ == "__main__":
  app.run(debug=True)
