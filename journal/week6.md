# Week 6 — Deploying Containers

## Provision ECS Cluster

I created an ECS cluster called cruddur

```sh
aws ecs create-cluster \
--cluster-name cruddur \
--service-connect-defaults namespace=cruddur
```

![create-cruddur-cluster-cli](/assets/create-cruddur-cluster-cli.png)

We need to create two health checks for `backend-flask` service.

1. One healthcheck will be an API endopoint, for the ELB
2. The second health check will be a script inside the docker container to be used by ECS

Inside app.py

```py
@app.route('/api/health-check')
def health_check():
  return {'success': True}, 200
```

![flask-api-healthcheck](/assets/flask-api-healthcheck.png)

This will provide a health check for the ELB.

The second health check is for the docker image to be run in ECS.

In `backend-flask/bin/flask/health-check`

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
except Exception as e:
  print(e)
  exit(1)  # false
```

make it executable with `chmod u+x`

## Create ECR repo and push image for backend-flask

First we need to login to ECR in order to be able to push and pull images.

```sh
aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
```

Create an ECR repo for the backend-flask's Python image, so that we don't need to pull it from dockerhub. This is more reliable.

```sh
aws ecr create-repository \
  --repository-name cruddur-python \
  --image-tag-mutability MUTABLE
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

Here it is locally
![cruddur-python-image](/assets/cruddur-python-image.png)

- Push it (upload) to ECR

```sh
docker push $ECR_PYTHON_URL:3.10-slim-buster
```

![flask-prod-image](/assets/flask-prod-image.png)

- edit Dockerfile to use the image from ECR

`FROM 632626636018.dkr.ecr.ca-central-1.amazonaws.com/cruddur-python:3.10-slim-buster`

We then create another image for the `backend-flask` service.

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

- tag it and upload (push)

```sh
docker tag backend-flask:latest $ECR_BACKEND_FLASK_URL:latest
docker push $ECR_BACKEND_FLASK_URL:latest
```

Here are the images on ECR:

![backend-images-on-ecr](/assets/backend-images-on-ecr.png)

## Deploy Backend Flask app as a service to Fargate

create a `service-execution-policy.json` file inside aws/policies with the content below:

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

![cruddur-parameter-store-acceess-policy](/assets/cruddur-parameter-store-acceess-policy.png)

This will allow us to store secrets in SSM Parameter store.

Create a 'service-assume-role-execution-policy.json". This is the trust policy for our role.

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

![cruddur-service-parameter-store](/assets/cruddur-service-parameter-store.png)

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

![Permission-policy-for-instance-tasks](/assets/Permission-policy-for-instance-tasks.png)

- We need to create CloudWatch Log Group to be used by our Task Definition in our cluster.

```sh
aws logs create-log-group --log-group-name "/cruddur/fargate-cluster"
aws logs put-retention-policy --log-group-name "/cruddur/fargate-cluster" --retention-in-days 1
```

![cruddur-cluster-log-group](/assets/cruddur-cluster-log-group.png)

- create an ECS Task Definition. Create a file in /aws/task-definitions/backend-flask.json, with the values for my own account, and the log group above.
- Register this task definition with ECS

```sh
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/backend-flask.json
```

We need to setup a security group

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

- install Session Manager for Linux on gitpod. This will allow us to login to ECR containers in case of troubleshooting

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

![backend-flask-running-on-ecr](/assets/backend-flask-running-on-ecr.png)
![backend-flask-running-on-ecr2](/assets/backend-flask-running-on-ecr2.png)

- for troubleshooting we can access the service task with

```sh
aws ecs execute-command  --region $AWS_DEFAULT_REGION --cluster cruddur --task arn:aws:ecs:ca-central-1:632626636018:task/cruddur/d6db1c03018847cea119684d59468c49 --container backend-flask --command "/bin/bash" --interactive
```

<!-- - create an ALB called cruddur-alb

  - this will require creating a new SG and a new target group
    -confirm ALB is working

- Now same as above we need to create a service for the front end
  This will be done with the file /aws/json/frontend-react-js.json

- make a prod dockerfile for frontend-react-js
- create nginex.conf file
- build a new prod docker image with

```sh
docker build \
--build-arg REACT_APP_BACKEND_URL="http://cruddur-alb-1554554041.ca-central-1.elb.amazonaws.com:4567" \
--build-arg REACT_APP_AWS_PROJECT_REGION="$AWS_DEFAULT_REGION" \
--build-arg REACT_APP_AWS_COGNITO_REGION="$AWS_DEFAULT_REGION" \
--build-arg REACT_APP_AWS_USER_POOLS_ID="ca-central-1_PHdtNYjuS" \
--build-arg REACT_APP_WEB_CLIENT_ID="1ams60e52fii48ogl892462cb" \
-t frontend-react-js \
-f Dockerfile.prod \
.
``` -->

- Create ECR repo for frontend-react-js

```sh
aws ecr create-repository \
  --repository-name frontend-react-js \
  --image-tag-mutability MUTABLE


export ECR_FRONTEND_REACT_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/frontend-react-js"
echo $ECR_FRONTEND_REACT_URL
```

- login to ECR and tag front-end image

```sh
docker tag frontend-react-js:latest $ECR_FRONTEND_REACT_URL:latest
```

-push it to ECR

```sh
docker push $ECR_FRONTEND_REACT_URL:latest
```

- register task definition

```sh
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/frontend-react-js.json
```

- create service

```sh
aws ecs create-service --cli-input-json file://aws/json/service-frontend-react-js.json
```

{% note %}

**Note:** In week3, as part of "Additional Homework" I created a seperate NodeJS service, as a JWT verfying sidecar. Since we are now
using ECS I need to convert this sidecar to an ECS service.

{% endnote %}

### Convert JWT verifyer sidecar

- create a docker image

```sh
cd sidecar-nodejs
docker build -t sidecar-nodejs .
```

- create ECR repo for the sidecar

```sh
aws ecr create-repository \
  --repository-name sidecar-nodejs \
  --image-tag-mutability MUTABLE

export ECR_SIDECAR_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/sidecar-nodejs"
echo $ECR_SIDECAR_URL
```

- tag the docker image and push it to ECR

```sh
docker tag sidecar-nodejs:latest $ECR_SIDECAR_URL:latest

docker push $ECR_SIDECAR_URL:latest
```

- create a task defintion file `/aws/task-definitions/sidecar-nodejs.json` with the correct settings and port

- using AWS Console create a target group for the sidecar, called `cruddur-sidecar-jwt-verifier-tg`. Using the ALB create a port 3050 lisitener
  to forward request to this TG

- create a service defintion file `/aws/json/service-jwt-verify.json`

- register task definition

```sh
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/sidecar-nodejs.json
```

- create and start the service

```sh
aws ecs create-service --cli-input-json file://aws/json/service-jwt-verify.json
```

- add healthcheck to frontend-react-js task definition

```json
"healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:3000 || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
```

## Secure Flask

- create a new Dockercompose.prod with `"--no-debug","--no-debugger","--no-reload"` flags passed to the run command
- build new prod docker image

```sh
docker build -t backend-flask -f Dockerfile.prod .
```

## Fix Cognito Refresh Tokens

Cognito by itself will automatically store the access token in local storage. It is unnecessary to store it again.
Here is a simpler getAccessToken function.

In `frontend-react/src/lib/checkAuth` add new function

```js
const getAccessToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getAccessToken().getJwtToken();
  } catch (err) {
    console.log(err);
  }
};
```

Then whenever you need the access token you can just get it from Cognito:

```js
const access_token = await getAccessToken();
const res = await fetch(backend_url, {
  headers: {
    Authorization: `Bearer ${access_token}`,
  },
  method: "GET",
});
```

Update all components and pages that require authorized API calls to use the above way of getting the `access_token`.

# Generate env variables using Ruby

# Fix Flask health-check
