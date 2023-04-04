# Week 6 — Deploying Containers

backend-flask/bin/db/test

```py
#!/usr/bin/env python3

import psycopg
import os
import sys

connection_url = os.getenv("CONNECTION_URL")

conn = None
try:
  print('attempting connection')
  conn = psycopg.connect(connection_url)
  print("Connection successful!")
except psycopg.Error as e:
  print("Unable to connect to the database:", e)
finally:
  conn.close()
```

This is for health check inside docker

- make it executable with `chmod u+x`

- Need healthcheck for Flask app. Inside app.py

```py
@app.route('/api/health-check')
def health_check():
  return {'success': True}, 200
```

This needs a flask healthcheck endpoint:
backend-flask/bin/flask/health-check

```py
#!/usr/bin/env python3

import urllib.request

try:
  response = urllib.request.urlopen('http://localhost:4567/api/health-check')
  if response.getcode() == 200:
    print("[OK] Flask server is running")
    exit(0)  # success
  else:
    print("[BAD] Flask server is not running")
    exit(1)  # false
# This for some reason is not capturing the error....
# except ConnectionRefusedError as e:
# so we'll just catch on all even though this is a bad practice
except Exception as e:
  print(e)
  exit(1)  # false
```


- Create CloudWatch Log Group

```sh
aws logs create-log-group --log-group-name "/cruddur/cluster"
aws logs put-retention-policy --log-group-name cruddur --retention-in-days 1
```

