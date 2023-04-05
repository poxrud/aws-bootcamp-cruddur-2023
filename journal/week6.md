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
aws logs create-log-group --log-group-name "/cruddur/fargate-cluster"
aws logs put-retention-policy --log-group-name "/cruddur/fargate-cluster" --retention-in-days 1
```

- Create ECS Cluster

```sh
aws ecs create-cluster \
--cluster-name cruddur \
--service-connect-defaults namespace=cruddur
```

- Create
  ECR repo for the backend-flask Python image, so that we don't need to pull it from dockerhub

```sh
aws ecr create-repository \
  --repository-name cruddur-python \
  --image-tag-mutability MUTABLE
```

- Login to ECR

```sh
aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
```

```sh
export ECR_PYTHON_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cruddur-python"
echo $ECR_PYTHON_URL
```

```sh
docker pull python:3.10-slim-buster
```

- tag it so that it can be uploaded to ECR

```sh
docker tag python:3.10-slim-buster $ECR_PYTHON_URL:3.10-slim-buster
```

- Push it (upload) to ECR

```sh
docker push $ECR_PYTHON_URL:3.10-slim-buster
```

- edit Dockerfile with

`FROM 632626636018.dkr.ecr.ca-central-1.amazonaws.com/cruddur-python:3.10-slim-buster`

- health check is working

- create another ECR for Flask

```sh
aws ecr create-repository \
  --repository-name backend-flask \
  --image-tag-mutability MUTABLE
```
