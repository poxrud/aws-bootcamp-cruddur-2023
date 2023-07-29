# Week X

*NOTE: Please read the final section at the end of this document, called [EXTRA CREDIT](#extra-credit) for a description of the additional homework challenges completed for week-x.*

# Week X Sync tool for static website hosting

We create a build script to build a static react version of the site and give
the execute permissions. This script is run to build the static site in the `build` directory. This will be sync'd to the S3 bucket.

```sh
bin/frontend/static-build
```

![build frontend](/assets/build-frontend.png)

For syncing, the `sync` ruby tool created by Andrew Brown is used. 
The tool requires setting of env variables for the S3 bucket and CloudFront
distribution id.

- create erb/sync.env.erb
- create bin/frontend/sync
- create /tmp/.keep

`bin/frontend/generate-env` is updated to generate a `sync.yaml` file required for the sync tool. 

The env vars are generated with:

```sh
bin/frontend/generate-env 
```

Andrew Brown's sync tool requires the installation of the following Ruby gems with:

```sh
gem install aws_s3_website_sync
gem install dotenv
```

and then is ran with:

```sh
bin/frontend/sync
```

Here is the result of syncing the static site:
![sync frontend](/assets/sync-frontend.png)
![frontend-on-s3](/assets/frontend-on-s3.png)
![front-end-sync-works](/assets/front-end-sync-works.png)

## Reconnect DB and Postgres Confirmation Lamba

run rds schema load and migrations
![postgres-prod-migration](/assets/postgres-prod-migration.png)

![postgres-uuid](/assets/postgres-uuid.png)

setup s3 custom error page forwarding to make SPA's work
```yml
CustomErrorResponses:
          - ErrorCode: 403
            ResponseCode: 200
            ResponsePagePath: /index.html
```
Here is forwarding working:
![cruddur-signin](/assets/cruddur-signin.png)

- put cognito `cruddur-post-confirmation` lambda into our private VPC
- create Security Group `CognitoLambdaSG`, and add it as incoming source in _RDS SG_

Here is `www.mycruddur.net` working with production postgresql connection.

![cruddur-home](/assets/cruddur-home.png)

## Fix CORS to use domain name for web-app
- CloudFormation Service fix CORS
  - edit `service/template.yaml` and `service/config.toml` with
  
  ```yml
  EnvFrontendUrl = 'https://mycruddur.net'
  EnvBackendUrl = 'https://api.mycruddur.net'
  ```

  - deploy  with `bin/cfn/service`

  - fix POST route for `/api/activities`, remove the hardcoded username
  - fix activity form to not be hardcoded in `ActivityForm.js`

## Ensure CI/CD pipeline works and create activity works
- fix cicd template.yml and the nested codebuild.yaml
- did a PR for prod
- checked pipeline
- build frontend and run `sync` tool
- verify changes on www.mycruddur.net

![codepipeline-success](/assets/codepipeline-success.png)
![codepipeline-success-frontend.png](/assets/codepipeline-success-frontend.png)

## Refactor to use JWT Decorator in Flask App

_NOTE_: In one of the previous weeks I implemented a JWT NodeJS based sidecar
to check JWT tokens. 

Here is the refactored JWT checking decorator shown below:
```python
  def jwt_required(f=None, on_error=None):
    if f is None:
      return partial(jwt_required, on_error=on_error)

    @wraps(f)
    def decorated_function(*args, **kwargs):
      auth_header = request.headers.get('Authorization')
      if (auth_header == None):
        if on_error:
          return on_error("token not provided")

        LOGGER.debug("token not provided")
        return {}, 401

      try:
        claims = CognitoJwtToken.verify(auth_header)
        g.cognito_user_id = claims['sub']
      except TokenVerifyError as e:
        # unauthenticated request
        LOGGER.debug(e)
        if on_error:
          return on_error(e)
        return {}, 401
      return f(*args, **kwargs)
    return decorated_function
```

## Refactor App.py
App.py has been refactored to remove all the _observability_ libraries into their own files.

```py
from lib.rollbar import init_rollbar
from lib.xray import init_xray
from lib.honeycomb import init_honeycomb
from lib.cors import init_cors
```
Routes have been removed from app.py and refactored as described in the section below.

## Refactor Flask Routes
The `App.py` has been made significantly smaller by refactoring routes for `users`, `activities`, and `messages` into their own directories and files. 

- All routes are in the `backend-flask/routes` directory

## Implement Replies
- fix frontend for sending `auth` token
- created `CreateReply.py` class
- created a new `reply.sql` file for inserting activity replies into the DB
- created a new migration for changing `reply_to_activity_uuid` type from `integer` to `uuid`
  - this required fixing a bug in migration script in the creation of timestamps. Sometimes the crated timestamps were incorrect because of dropping of the decimal parts of the timestamp. The solution was to generate the migration timestamp with the following code:
  ```python
     timestamp = int(datetime.now(timezone.utc).timestamp())
  ```

![activity_uuid_migration](/assets/activity_uuid_migration.png)

- add `replies` json array to `home.sql`
  ```sql
    (SELECT COALESCE(array_to_json(array_agg(row_to_json(array_row))),'[]'::json) FROM (
  SELECT
    replies.uuid,
    reply_users.display_name,
    reply_users.handle,
    replies.message,
    replies.replies_count,
    replies.reposts_count,
    replies.likes_count,
    replies.reply_to_activity_uuid,
    replies.created_at
  FROM public.activities replies
  LEFT JOIN public.users reply_users ON reply_users.uuid = replies.user_uuid
  WHERE
    replies.reply_to_activity_uuid = activities.uuid
  ORDER BY  activities.created_at ASC
  ) array_row) as replies
  ```
- fixed CSS so that replies are off to the right of the parent message

![frontend-css-replies](/assets/frontend-css-replies.png)

## Improved Error Handling for the app

- move the activities json array from home.sql to show.sql
- modify `ReplyForm.js` and `ActivityForm` to show errors
  - do this by adding `FormErrors.js` and `FormErrorItem.js` components and their css
- add better errors to Signup and Signin Page using `<FormErrors/>` component

![frontend-reply-errors](/assets/frontend-reply-errors.png)
![frontend-reply-errors2](/assets/frontend-reply-errors2.png)

- refactor `post`, `put`, `get`, `delete` into `lib/Requests.js` and update our forms.
  - The following files were refactored with the new `post` and `get` methods:
    - ActivityForm.js
    - MessageForm.js
    - ProfileForm.js
    - ReplyForm.js
    - HomeFeedPage.js
    - MessageGroupNewPage.js
    - MessageGroupPage.js
    - MessageGroupsPage.js
    - NotificationsFeedPage.js
    - UserFeedPage.js

## Activities Show Page

- In `ActivityContent.js` make only name and photo clickable 
- Create `ActivityShowPage.js` page and css
- Add User status route to show user activities.
  - in `backend-flask/routes/users.py`

  ```py
    @app.route("/api/activities/@<string:handle>/status/<string:activity_uuid>", methods=['GET'])
      def data_show_activity(handle, activity_uuid):
        data = ShowActivity.run(activity_uuid)
        return data, 200
  ```

  with the following `show_activity.py` class:

  ```py
  class ShowActivity:
  def run(activity_uuid):

    sql = db.template('activities', 'show')
    results = db.query_object_json(sql, {
      'uuid': activity_uuid
    })
  ```

  - In react-frontend create `ActivityShowPage` and associated components and styling to show all the replies to a specific activity. 

  ![replies-screen](/assets/replies-screen.png)

 
 # More General Cleanup Part 1 and Part 2

 - run migration on prod
 ```sh
 CONNECTION_URL=$PROD_CONNECTION_URL bin/db/migrate
 ```

 - update _backend_ and _frontend_ on _production_
  - for backend merge week-x into prod and check CodePipeline for success
  - for frontend:
    - run `bin/frontend/static-build`
    - rub `bin/frontend/sync`

- fix DynamoDB connection to use env vars for table name and DynamoDB endpoint url. 
  - edit `backend-flask.env.erb``
  - edit `aws/cfn/service/template.yaml`  and `config.toml`
  - deploy to _cloudformation_ and execute changeset

- create a machine user for DynamoDB access using CloudFormation
  - deploy using `bin/cfn/machineuser`

![cruddur_machine_user_created](/assets/cruddur_machine_user_created.png)

Here we can see that dynamodb works because we can send direct messages to users.

![crudur_messaging_on_prod](/assets/crudur_messaging_on_prod.png)
      

# EXTRA CREDIT

## Github Actions Workflow for Building and Syncing Frontend Assets
I created a GitHub Actions workflow that builds the frontend assets, and syncs them with the existing s3 `www.mycrudder.net` bucket. It then invalidates the CloudFront distribution for the `www.mycruddur.net` website.

This workflow gets triggered on pushes or pull request merges into the `prod-frontend` branch. 

Here is the GitHub Actions workflow file, that can be found in:
- `.github/workflows/frontend-deploy.yml`

```yml
# Build and Deploy the frontend assets to AWS S3

name: Deploy frontend

on:
  push:
    branches: [prod-frontend]

env:
  AWS_REGION: "ca-central-1"
  BUCKET: "www.mycruddur.net"
  CF_DISTRIBUTION_ID: "E19FFCVDAGBBCT"

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-22.04

    steps:
      - uses: actions/checkout@v3

      - name: Use Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "18.x"

      - name: Install npm packages
        run: |
          cd frontend-react-js
          npm i

      - name: Build prod
        continue-on-error: true
        run: ./bin/frontend/static-build

      - name: configure aws credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::632626636018:role/GitHubActionsRole
          role-session-name: GitHub_OIDC
          aws-region: ${{env.AWS_REGION}}

      - name: sync frontend website and create CF invalidation
        run: |
          aws s3 sync frontend-react-js/build/ s3://${{env.BUCKET}}/
          aws cloudfront create-invalidation --distribution-id ${{env.CF_DISTRIBUTION_ID}} --paths "/*"

```
The Workflow executes the following steps:
- set up NodeJS
- install npm packages for the project
- builds a static site for production
- uses AWS credentials by assuming an AWS Role
- syncs the frontend using the `aws s3 sync` command
- invalidates the CloudFormation distribution

![github_actions_assets_build](/assets/github_actions_assets_build.png)

### GitHub Actions Authentication and Roles

Github authenticates with AWS through the use of the `IAM OIDCProvider`. The IODCProvider assigns GitHub an _IAM Role_ with the permissions to sync to the `www.mycruddur.net` bucket and invoke a cloudfront invalidation. GitHub assumes this Role when running AWS cli commands.

The OIDCProvider, the GitHub access Role and its Trust and Permission policies were all created using CloudFormation. Under the `CrdSyncRole` stack name.

Here is CloudFormation template:

- `aws/cfn/github/template.yml`

```yml
AWSTemplateFormatVersion: "2010-09-09"

Parameters:
  WwwBucketName:
    Type: String
  distributionId:
    Type: String

Resources:
  GitHubOIDCProvider:
    Type: "AWS::IAM::OIDCProvider"
    Properties:
      ClientIdList:
        - "sts.amazonaws.com"
      ThumbprintList:
        - "6938fd4d98bab03faadb97b34396831e3780aea1"
      Url: https://token.actions.githubusercontent.com

  GitHubActionsRole:
    Type: "AWS::IAM::Role"
    Properties:
      RoleName: "GitHubActionsRole"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Federated: !Sub "arn:aws:iam::${AWS::AccountId}:oidc-provider/token.actions.githubusercontent.com"
            Action: "sts:AssumeRoleWithWebIdentity"
            Condition:
              StringEquals:
                {
                  "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                  "token.actions.githubusercontent.com:sub": "repo:poxrud/aws-bootcamp-cruddur-2023:ref:refs/heads/prod-frontend",
                }
  SyncToS3BucketPermission:
    Type: "AWS::IAM::Policy"
    Properties:
      PolicyName: SyncToS3BucketPolicy
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action:
              - "s3:PutObject"
              - "s3:DeleteObject"
              - "s3:ListBucket"
            Resource:
              - !Sub "arn:aws:s3:::${WwwBucketName}"
              - !Sub "arn:aws:s3:::${WwwBucketName}/*"
          - Effect: Allow
            Action:
              - "cloudfront:CreateInvalidation"
            Resource:
              - !Sub "arn:aws:cloudfront::632626636018:distribution/${distributionId}"
      Roles:
        - !Ref GitHubActionsRole

```

 
 Please note that the role has a trust policy that only allows connections from the `poxrud/aws-bootcamp-cruddur-2023` repo and the `prod-frontend` branch. 

 This is accomplished with the Condition as described below:

 ```yml
  Action: "sts:AssumeRoleWithWebIdentity"
  Condition:
    StringEquals:
      {
        ...
        "token.actions.githubusercontent.com:sub": "repo:poxrud/aws-bootcamp-cruddur-2023:ref:refs/heads/prod-frontend",
      }
 ```

The stack is executed with the following bin script:

- `bin/cfn/github`

```sh
#! /usr/bin/env bash
set -e # stop the execution of the script if it fails

CFN_PATH="/workspace/aws-bootcamp-cruddur-2023/aws/cfn/github/template.yaml"
CONFIG_PATH="/workspace/aws-bootcamp-cruddur-2023/aws/cfn/github/config.toml"
echo $CFN_PATH

cfn-lint $CFN_PATH

BUCKET=$(cfn-toml key deploy.bucket -t $CONFIG_PATH)
REGION=$(cfn-toml key deploy.region -t $CONFIG_PATH)
STACK_NAME=$(cfn-toml key deploy.stack_name -t $CONFIG_PATH)
PARAMETERS=$(cfn-toml params v2 -t $CONFIG_PATH)

aws cloudformation deploy \
  --stack-name $STACK_NAME \
  --s3-bucket $BUCKET \
  --s3-prefix github-actions \
  --region $REGION \
  --template-file "$CFN_PATH" \
  --no-execute-changeset \
  --tags group=github-actions-IODC \
  --parameter-overrides $PARAMETERS \
  --capabilities CAPABILITY_NAMED_IAM
```

Here is a successful update to the production website. The Title was changed locally from "Home" to "Home MyCruddur" and then the changes were pushed to `prod-frontend`

![](/assets/github_actions_deploy_success.png)

## Root domain forwarding to www

In order to create a better user experience and improved SEO, I implemented
the following website forwarding rules for the _mycruddur.net_ website:

- `https://mycruddur.net`    => `https://www.mycruddur.net`
- `http://mycruddur.net`     => `https://www.mycruddur.net`
- `http://www.mycruddur.net` => `https://www.mycruddur.net`

These forwarding rules can be verified by visiting the above URL's. 

Implementing these forwarding rules required changes to S3, R53, and CloudFront. 

### Implementation  
To achieve this required two S3 buckets and two CloudFront distributions. 

#### Bucket 1
- This is a public bucket that is called `www.mycruddur.net` and hosts the static frontend assets for the website.

#### Bucket 2
This is a public bucket that is called `mycruddur.net` and is setup to forward requests to `www.mycruddur.net`

![root_bucket_redirect](/assets/root_bucket_redirect.png)

#### Main CloudFront Distribution for www.mycruddur.net
This is the main distribution that will cache and forward requests to the `www.mycruddur.net` bucket. `R53` will point the `www` `Alias` record to this distribution.

This distribution is also setup to redirect _http_ to _https_

#### Second CloudFront Distribution for mycruddur.net
`R53` will forward the root domain `mycruddur.net` to this distribution, through an `Alias` record. This distribution will then forward to the s3 bucket `mycruddur.net`, which will then forward to `https://www.mycruddur.net`

The only reason this distribution is required is for its HTTPS termination. If we did not require https then it would be possible to directly forward R53 => S3 bucket. 

To summarize:
- R53 (www.mycruddur.net) => CloudFlare Distribution 1 => S3 (www.mycruddur.net)
- R53 (mycruddur.net) => CloudFlare Distribution 2 => S3 (mycruddur.net) => (www.mycruddur.net)
