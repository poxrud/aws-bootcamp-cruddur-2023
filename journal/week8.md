# Week 8 — Serverless Image Processing

- npm install aws-cdk -g

- in .gitpod.yml

```yml
- name: cdk
    before: |
      npm install aws-cdk -g
```

- `cdk synth`

- bootstrap

```sh
gitpod /workspace/aws-bootcamp-cruddur-2023/thumbing-serverless-cdk (main) $ cdk bootstrap "aws://632626636018/ca-central-1"
 ⏳  Bootstrapping environment aws://632626636018/ca-central-1...
Trusted accounts for deployment: (none)
Trusted accounts for lookup: (none)
Using default execution policy of 'arn:aws:iam::aws:policy/AdministratorAccess'. Pass '--cloudformation-execution-policies' to customize.
CDKToolkit: creating CloudFormation changeset...
 ✅  Environment aws://632626636018/ca-central-1 bootstrapped.
 ```

 - `cdk deploy`

 - .env.example

 `cp .env.example .env` inside .gitpod.yml. This is because .env is ignored with our gitignore

 ```yml
THUMBING_BUCKET_NAME="assets.mycruddur.net"
THUMBING_FUNCTION_PATH="/workspace/aws-bootcamp-cruddur-2023/aws/lambdas/process-images/"
THUMBING_S3_FOLDER_INPUT="avatars/original"
THUMBING_S3_FOLDER_OUTPUT="avatars/processed"
THUMBING_WEBHOOK_URL="api.mycruddur.net/webhooks/avatar"
THUMBING_TOPIC_NAME="cruddur-assets"
```

- create inside /aws/lambdas/process-images
-- index.js
-- test.js
-- s3-image-processing.js
-- example.json

initialize the folder as npm so that we could install sharpjs and run tests

```sh
cd /aws/lambdas/process-images
npm init -y
npm i sharp
```

install s3 client

```sh
npm i @aws-sdk/client-s3
```

- deply with `cdk deploy`

- build sharp libarary for production. Use instructions here:
https://sharp.pixelplumbing.com/install#aws-lambda
```sh
rm -rf nodule_modules/sharp
SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install --arch=x64 --platform=linux --libc=glibc sharp
```

- inside `/thumbing-serverless-cdk-stack.ts` in the bottom of the constructor, add code to create s3 bucked event, to trigger a lambda on file uploads. Using this code:

```typescript
this.createS3NotifyToLambda(folderInput, lambda, bucket)
```

Then add the function `createS3NotifyToLambda` to the class.

Then try it out with `cdk synth` and if all is good deploy with `cdk deploy`.

```typescript
 importBucket(bucketName: string): s3.IBucket {
    const bucket = s3.Bucket.fromBucketName(this, "AssetsBucket", bucketName);
    return bucket;
  }
```
 
 - Manually create s3 bucket `assets.mycruddur.net` w
 
 - Give our Lambda permissions to write to s3

 ```ts
   createPolicyBucketAccess(bucketArn: string){
    const s3ReadWritePolicy = new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
      ],
      resources: [
        `${bucketArn}/*`,
      ]
    });
    return s3ReadWritePolicy;
  }
```

- attach the policy to our lambda

```ts
lambda.addToRolePolicy(s3ReadWritePolicy);
```

- manually upload a large photo and check that a processed version was correctly placed in `avatars/processed`

- create SNS Topic, SNS Subscription, for webhook, on processed images
by modifying `thumbing-serverless.cdk-stack.ts`

## Serve Avatars via CloudFront

- setup CloudFront distribution
- Point it to S3 bucket
- Give bucket permission policy to allow CloudFront to access it
- Point R53 assets.mycruddur.net to point to the CloudFront distribution

- Change architecture to use a different bucket for uploads, and another for processed images

```yml
UPLOADS_BUCKET_NAME="mycruddur-uploaded-avatars"
ASSETS_BUCKET_NAME="assets.mycruddur.net"
ASSETS_FUNCTION_PATH="/workspace/aws-bootcamp-cruddur-2023/aws/lambdas/process-images/"
THUMBING_S3_FOLDER_INPUT="avatars/original"
THUMBING_S3_FOLDER_OUTPUT="avatars/processed"
THUMBING_WEBHOOK_URL="https://api.mycruddur.net/webhooks/avatar"
THUMBING_TOPIC_NAME="cruddur-assets"
```


- getting Task Time out error

```
Task timed out after 3.08 seconds
```
Need to increase Lambda's timeout to 10 seconds.

## Implement Users Profile Page


```py
#app.py

@app.route("/api/profile/update", methods=['POST','OPTIONS'])
@cross_origin()
def data_update_profile():

  auth_header = request.headers.get('Authorization')

  if (auth_header == None):
    LOGGER.debug("auth token not provided")
    return {}, 401

  bio          = request.json.get('bio',None)
  display_name = request.json.get('display_name',None)
  
  try:
    claims = CognitoJwtToken.verify(auth_header)
    cognito_user_id = claims['sub']
    model = UpdateProfile.run(
      cognito_user_id=cognito_user_id,
      bio=bio,
      display_name=display_name
    )
    if model['errors'] is not None:
      return model['errors'], 422
    else:
      return model['data'], 200
  except TokenVerifyError as e:
    # unauthenicatied request
    LOGGER.debug(e)
    return {}, 401
```


- make backend-flask/db/sql/users/update.sql

```sql
UPDATE public.users 
SET 
  bio = %(bio)s,
  display_name= %(display_name)s
WHERE 
  users.cognito_user_id = %(cognito_user_id)s
RETURNING handle;
```

- add db migration generator in order to add a new "bio" field to our users table in the db

```sql
CREATE TABLE IF NOT EXISTS public.schema_information (
  id integer UNIQUE,
  last_successful_run text
);
INSERT INTO
  public.schema_information (id, last_successful_run)
VALUES(1, '0') ON CONFLICT (id) DO NOTHING;
```
## Presigned URL generation via Ruby Lambda

```sh
export UPLOADS_BUCKET_NAME="mycruddur-uploaded-avatars"
gp env UPLOADS_BUCKET_NAME="mycruddur-uploaded-avatars"
```
 
- add Lambda code to create presigned PUT url's for uploading

- add Lambda code for the JWT verificaiton and authorization
  - in aws/lambdas/lambda-authorizer

```js
"use strict";
const { CognitoJwtVerifier } = require("aws-jwt-verify");

const jwtVerifier = CognitoJwtVerifier.create({
  userPoolId: process.env.USER_POOL_ID,
  tokenUse: "access",
  clientId: process.env.CLIENT_ID
});

exports.handler = async (event) => {
  console.log("request:", JSON.stringify(event, undefined, 2));

  const jwt = event.headers.authorization;
  try {
    const payload = await jwtVerifier.verify(jwt);
    console.log("Access allowed. JWT payload:", payload);
  } catch (err) {
    console.error("Access forbidden:", err);
    return {
      isAuthorized: false,
    };
  }
  return {
    isAuthorized: true,
  };
};
```

also need to install jwt npm package

```sh
npm i aws-jwt-verify
```

- zip up the lambda-authorizer folder

```sh
gitpod /workspace/aws-bootcamp-cruddur-2023/aws/lambdas (main) $ zip -r lambda-authorizer.zi[ lambda-authorizer/
  adding: lambda-authorizer/ (stored 0%)
  adding: lambda-authorizer/index.js (deflated 44%)
  adding: lambda-authorizer/package.json (deflated 35%)
  adding: lambda-authorizer/node_modules/ (stored 0%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/ (stored 0%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/LICENSE (deflated 65%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/ (stored 0%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/ (stored 0%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/asn1.js (deflated 74%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/assert.js (deflated 76%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/cognito-verifier.js (deflated 71%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/error.js (deflated 77%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/https-common.js (deflated 52%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/https-node.js (deflated 60%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/https.js (deflated 62%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/index.js (deflated 53%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/jwk.js (deflated 74%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/jwt-model.js (deflated 30%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/jwt-rsa.js (deflated 78%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/jwt.js (deflated 74%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/node-web-compat-node.js (deflated 62%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/node-web-compat-web.js (deflated 59%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/node-web-compat.js (deflated 40%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/safe-json-parse.js (deflated 52%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/typing-util.js (deflated 19%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/cjs/package.json (deflated 34%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/ (stored 0%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/asn1.js (deflated 74%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/assert.js (deflated 76%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/cognito-verifier.js (deflated 71%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/error.js (deflated 71%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/https-common.js (deflated 50%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/https-node.js (deflated 60%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/https.js (deflated 61%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/index.js (deflated 27%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/jwk.js (deflated 73%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/jwt-model.js (deflated 18%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/jwt-rsa.js (deflated 78%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/jwt.js (deflated 73%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/node-web-compat-node.js (deflated 63%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/node-web-compat-web.js (deflated 60%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/node-web-compat.js (deflated 41%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/safe-json-parse.js (deflated 50%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/typing-util.js (deflated 16%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/dist/esm/package.json (deflated 34%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/package.json (deflated 71%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/README.md (deflated 75%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/asn1.d.ts (deflated 59%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/assert.d.ts (deflated 75%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/cognito-verifier.d.ts (deflated 72%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/error.d.ts (deflated 76%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/https-common.d.ts (deflated 41%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/https-node.d.ts (deflated 48%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/https.d.ts (deflated 63%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/index.d.ts (deflated 33%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/jwk.d.ts (deflated 74%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/jwt-model.d.ts (deflated 72%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/jwt-rsa.d.ts (deflated 77%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/jwt.d.ts (deflated 63%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/safe-json-parse.d.ts (deflated 48%)
  adding: lambda-authorizer/node_modules/aws-jwt-verify/typing-util.d.ts (deflated 65%)
  adding: lambda-authorizer/node_modules/.package-lock.json (deflated 35%)
  adding: lambda-authorizer/package-lock.json (deflated 46%)
  ```

- grab the API Gateway URL and update our .env frontend files with this.
  - in /frontend-react-js/Dockerfile.prod add:
  ```yml
  ARG REACT_APP_API_GATEWAY_ENDPOINT_URL
  ENV REACT_APP_API_GATEWAY_ENDPOINT_URL=$REACT_APP_API_GATEWAY_ENDPOINT_URL
  ```

  also add this to the .erb file:

  ```yml
REACT_APP_API_GATEWAY_ENDPOINT_URL=<%= ENV['REACT_APP_API_GATEWAY_ENDPOINT_URL']%>  ```

  inside gitpod cli

  ```sh
  $ export REACT_APP_API_GATEWAY_ENDPOINT_URL="https://hx6xrw3sta.execute-api.ca-central-1.amazonaws.com"
  gp env REACT_APP_API_GATEWAY_ENDPOINT_URL="https://hx6xrw3sta.execute-api.ca-central-1.amazonaws.com"
  ```



- edit ProfileForm.js

- install ruby Gemfiles dependencies, zip it up and upload to AWS Lambda

```sh
bundle config set --local path 'vendor/bundle' \ 
bundle install
```