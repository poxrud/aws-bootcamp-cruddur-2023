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

Here is the health check:

![backend-api-check-on-public-ELB.png](/assets/backend-api-check-on-public-ELB.png)

- for troubleshooting we can access the service task with

```sh
aws ecs execute-command  --region $AWS_DEFAULT_REGION --cluster cruddur --task arn:aws:ecs:ca-central-1:632626636018:task/cruddur/d6db1c03018847cea119684d59468c49 --container backend-flask --command "/bin/bash" --interactive
```

## Create ECR repo and push image for fronted-react-js

```sh
aws ecr create-repository \
  --repository-name frontend-react-js \
  --image-tag-mutability MUTABLE


export ECR_FRONTEND_REACT_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/frontend-react-js"
echo $ECR_FRONTEND_REACT_URL
```

- make a prod dockerfile for frontend-react-js
- create nginex.conf file inside frontend-react-js
- build a new prod docker image with

- login to ECR and tag the frontend-react-js image

```sh
docker tag frontend-react-js:latest $ECR_FRONTEND_REACT_URL:latest
```

-push it to ECR

```sh
docker push $ECR_FRONTEND_REACT_URL:latest
```

Here it is on ECR:
![images-on-ecr](/assets/images-on-ecr.png)

## Deploy Frontend React JS app as a service to Fargate

- create a task definition inside task-definitions/frontend-react-js.json

```json
{
  "family": "frontend-react-js",
  "executionRoleArn": "arn:aws:iam::632626636018:role/CruddurServiceExecutionRole",
  "taskRoleArn": "arn:aws:iam::632626636018:role/CruddurTaskRole",
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512",
  "requiresCompatibilities": ["FARGATE"],
  "containerDefinitions": [
    {
      "name": "frontend-react-js",
      "image": "632626636018.dkr.ecr.ca-central-1.amazonaws.com/frontend-react-js",
      "essential": true,
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:3000 || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "portMappings": [
        {
          "name": "frontend-react-js",
          "containerPort": 3000,
          "protocol": "tcp",
          "appProtocol": "http"
        }
      ],

      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/cruddur/fargate-cluster",
          "awslogs-region": "ca-central-1",
          "awslogs-stream-prefix": "frontend-react-js"
        }
      },
      "environment": [
        { "name": "REACT_AWS_PROJECT_REGION", "value": "ca-central-1" },
        { "name": "REACT_APP_AWS_COGNITO_REGION", "value": "ca-central-1" },
        {
          "name": "REACT_APP_AWS_USER_POOLS_ID",
          "value": "ca-central-1_PHdtNYjuS"
        },
        {
          "name": "REACT_APP_WEB_CLIENT_ID",
          "value": "1ams60e52fii48ogl892462cb"
        }
      ]
    }
  ]
}
```

- register task definition for frontend-react-js

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

- Edit `aws/json/service-backend-flask.json` and add the sidecar image to the list of containers to run as part of the
  backend-flask task. A task can have many containers running.

```json
...
      "name": "verify-cognito-token",
      "image": "632626636018.dkr.ecr.ca-central-1.amazonaws.com/sidecar-nodejs",
      "essential": true,
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:3050/health-check || exit 1"
        ]
      },
...
```

Also add the env variables required for the sidecar to run.

## Provision and configure Application Load Balancer along with target groups

- use and AWS Console to create an ALB called cruddur-alb

![cruddur-alb.png](/assets/cruddur-alb.png)

- this will require creating a new SG and a new target group

![cruddur-alb-sg.png](/assets/cruddur-alb-sg.png)

- create a new `backend-flask` production image that points to the ELB

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
```

- push the image. Confirm that the ALB works.

![backend-api-check-on-public-ELB.png](/assets/backend-api-check-on-public-ELB.png)

## Manage your domain useing Route53 via hosted zone

Using R53 I registered my domain name _mycruddur.net_
![mycruddur-r53-domain](/assets/mycruddur-r53-domain.png)

## Create an SSL cerificate via ACM

Here it is:
![mycruddur-ssl-cert](/assets/mycruddur-ssl-cert.png)

## Setup a record set for naked domain to point to frontend-react-js

Using R53 I created an Alias record to point the naked domain _mycruddur.net_ to the load balancer that was configured above.

![mycruddur-r53-alias](/assets/mycruddur-r53-alias.png)

## Setup a record set for api subdomain to point to the backend-flask

I created an alias in R53 to point `api.mycruddur.net` to the load balancer greated above. You can see the record in the screenshot immidiatly above this section.

## Configure CORS to only permit traffic from our domain

Using the _cruddur-alb_ ALB that we setup before we can configure rules to do the following:

- forward port 80 traffic to port 443. This will make sure we're always using https
- Forward all api.mycruddur.net calls to the backend-flask service target group
- Forward all mycruddur.net calls to the frontend-react-js service target group
- Deny everything else, this makes sure that we only permit traffic from our domain

The rules above work by checking the `Host `header.

![mycruddur-alb-rules](/assets/mycruddur-alb-rules.png)

## Secure Flask by not running in debug mode

- create a new Dockercompose.prod with `"--no-debug","--no-debugger","--no-reload"` flags passed to the run command
- build new prod docker image

```sh
docker build -t backend-flask -f Dockerfile.prod .
```

Push the new image to ECR, force a new backend-flask deploy.

## Implement Refresh Token for Amazon Cognito

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

# Refactor bin directory to be top level

The bin files inside `backend-flask/bin` have been moved to `/bin` inside the root project folder. To accomplish this relative paths inside the scripts needed to be updated.

To get the absolute path of where every script is being ran from, the following command was used:

```sh
ABS_PATH=$(readlink -f "$0")
```

This combined with `dirname` allowed the scripts to be ran from any location.
Here is an example of using this strategy in one of the scripts, to get locations for the different project and service paths:

```sh
ABS_PATH=$(readlink -f "$0")
BACKEND_PATH=$(dirname $ABS_PATH)
BIN_PATH=$(dirname $BACKEND_PATH)
PROJECT_PATH=$(dirname $BIN_PATH)
BACKEND_FLASK_PATH="$PROJECT_PATH/backend-flask"
```

## Configure task defintions to contain x-ray and turn on Container Insights

Using the AWS console, I navigated to the ECS Cluster, and clicked on _Update Cluster" and enabled \_Container Insights_.
![mycruddur-container-insights](/assets/mycruddur-container-insights.png)

Inside `aws/task-definitions/backend-flask.json` and `aws/task-definitions/frontend-react-js.json`:

- add a section "containerDefinitions : []", and inside the square brackets add:

```json
{
  "name": "xray",
  "image": "public.ecr.aws/xray/aws-xray-daemon",
  "essential": true,
  "user": "1337",
  "portMappings": [
    {
      "name": "xray",
      "containerPort": 2000,
      "protocol": "udp"
    }
  ]
},
```

## Change Docker Compose to explicitly use a user-defined network

Edit the bottom of `docker-compose.yml` to have have a `networks:` section.
The section will name the network that services within docker-compose will share. This will allow docker containers outside of the docker-compose file to communicated with containers inside the file.

```yml
networks:
  cruddur-net:
    driver: bridge
    name: cruddur-net
```

## Using ruby generate out env dot files for docker using erb templates

# Generate env variables using Ruby

Docker-compose.yml can be setup to use env files for its envrionmental variables instead of passing them directly in the `Environment` section. Since we have a frontend-react-js and a backend-flask services we need to generate two env files to be used by docker-compose.yml

A ruby script in /bin/backend/generate is used to generate the env file for the backend-flask env file called `/backend-flask.env`

```ruby
#!/usr/bin/env ruby

require 'erb'

template = File.read 'erb/backend-flask.env.erb'
content = ERB.new(template).result(binding)
filename = "backend-flask.env"
File.write(filename, content)
```

A ruby script in /bin/frontend/generate is used to generate the env file for the frontend-react-js env file called `/frontend-react-js.env`

```ruby
#!/usr/bin/env ruby

require 'erb'

template = File.read 'erb/frontend-react-js.env.erb'
content = ERB.new(template).result(binding)
filename = "frontend-react-js.env"
File.write(filename, content)
```

The ruby script uses `ERB` templates in `/erb/` to generate the env files.

NOTE: it is important to add `*.env` to the end of the `.gitignore` file so that we do not accidently commit secrets to github.
