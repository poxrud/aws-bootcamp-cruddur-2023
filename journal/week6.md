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

- set env variable

```sh
export ECR_BACKEND_FLASK_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/backend-flask"
```

- build a new docker image for backend-flask:

```sh
docker build -t backend-flask .
```

- tag it for upload (push)

```sh
docker tag backend-flask:latest $ECR_BACKEND_FLASK_URL:latest
```

- create a `service-execution-policy.json` file inside aws/policities
  with the content below:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameters", "ssm:GetParameter"],
      "Resource": "arn:aws:ssm:ca-central-1:632626636018:parameter/cruddur/backend-flask/*"
    }
  ]
}
```

- Create a 'service-assume-role-execution-policy.json". This is the trust policy for our role.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": ["sts:AssumeRole"],
      "Effect": "Allow",
      "Principal": {
        "Service": ["ecs-tasks.amazonaws.com"]
      }
    }
  ]
}
```

- Create env variables in the Systems Parameter Store using CLI

```sh
aws ssm put-parameter --type "SecureString" --name "/cruddur/backend-flask/AWS_ACCESS_KEY_ID" --value $AWS_ACCESS_KEY_ID
aws ssm put-parameter --type "SecureString" --name "/cruddur/backend-flask/AWS_SECRET_ACCESS_KEY" --value $AWS_SECRET_ACCESS_KEY
aws ssm put-parameter --type "SecureString" --name "/cruddur/backend-flask/CONNECTION_URL" --value $PROD_CONNECTION_URL
aws ssm put-parameter --type "SecureString" --name "/cruddur/backend-flask/ROLLBAR_ACCESS_TOKEN" --value $ROLLBAR_ACCESS_TOKEN
aws ssm put-parameter --type "SecureString" --name "/cruddur/backend-flask/OTEL_EXPORTER_OTLP_HEADERS" --value "x-honeycomb-team=$HONEYCOMB_API_KEY"
```

- Create a Task execution role with an ec2 assumerole trust policy

```sh
aws iam create-role --role-name CruddurServiceExecutionRole --assume-role-policy-document file://aws/policies/service-assume-role-execution-policy.json
```

- Attach policy to the execution role

```sh
aws iam put-role-policy \
  --policy-name CruddurServiceExecutionPolicy \
  --role-name CruddurServiceExecutionRole \
  --policy-document file://aws/policies/service-execution-policy.json
```

- Create Task Role

```sh
aws iam create-role \
    --role-name CruddurTaskRole \
    --assume-role-policy-document "{
  \"Version\":\"2012-10-17\",
  \"Statement\":[{
    \"Action\":[\"sts:AssumeRole\"],
    \"Effect\":\"Allow\",
    \"Principal\":{
      \"Service\":[\"ecs-tasks.amazonaws.com\"]
    }
  }]
}"

aws iam put-role-policy \
  --policy-name SSMAccessPolicy \
  --role-name CruddurTaskRole \
  --policy-document "{
  \"Version\":\"2012-10-17\",
  \"Statement\":[{
    \"Action\":[
      \"ssmmessages:CreateControlChannel\",
      \"ssmmessages:CreateDataChannel\",
      \"ssmmessages:OpenControlChannel\",
      \"ssmmessages:OpenDataChannel\"
    ],
    \"Effect\":\"Allow\",
    \"Resource\":\"*\"
  }]
}
"
aws iam attach-role-policy --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess --role-name CruddurTaskRole

aws iam attach-role-policy --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess --role-name CruddurTaskRole
```

- create an ECS Task Definition. Create a file in /aws/task-definitions/backend-flask.json, with the values for my own account.
- Register this task definition with ECS

```sh
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/backend-flask.json
```

- We need to setup a security group

  - get default VPC:

  ```sh
    export DEFAULT_VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault, Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)
    echo $DEFAULT_VPC_ID
  ```

  - create the SG

    ```sh
      gitpod /workspace/aws-bootcamp-cruddur-2023 (week6) $ export CRUD_SERVICE_SG=$(aws ec2 create-security-group \
      --group-name "crud-srv-sg" \
      --description "Security group for Cruddur services on ECS" \
      --vpc-id $DEFAULT_VPC_ID \
      --query "GroupId" --output text)
      echo $CRUD_SERVICE_SG
      sg-0f7dd960458eed278

      aws ec2 authorize-security-group-ingress \
      --group-id $CRUD_SERVICE_SG \
      --protocol tcp \
      --port 4567 \
      --cidr 0.0.0.0/0

    ```

- Fix ECS IAM Policy to give it access to ECR, by adding the below to
  service-execution-policy.json

```sh
{
  "Effect": "Allow",
  "Action": ["ecr:GetAuthorizationToken"],
  "Resource": "*"
}
```

- Attach full cloudwatch permissions

```sh
aws iam attach-role-policy --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess --role-name CruddurServiceExecutionRole
```

- install Session Manager for Linux on gitpod

```sh
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb

gitpod /workspace/aws-bootcamp-cruddur-2023 (week6) $ session-manager-plugin

The Session Manager plugin was installed successfully. Use the AWS CLI to start a session.
```

- Get our subnet id's

```sh
export DEFAULT_SUBNET_IDS=$(aws ec2 describe-subnets  \
 --filters Name=vpc-id,Values=$DEFAULT_VPC_ID \
 --query 'Subnets[*].SubnetId' \
 --output json | jq -r 'join(",")')
echo $DEFAULT_SUBNET_IDS

```

- Create a /aws/json/service-backend-flask.json, use the subnet ID's from above
- run with

```sh
aws ecs create-service --cli-input-json file://aws/json/service-backend-flask.json
```

- we access the service task with

```sh
aws ecs execute-command  --region $AWS_DEFAULT_REGION --cluster cruddur --task arn:aws:ecs:ca-central-1:632626636018:task/cruddur/d6db1c03018847cea119684d59468c49 --container backend-flask --command "/bin/bash" --interactive
```

- modify the default SG to allow connections from ECS SG, this will fix RDS health check
