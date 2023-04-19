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
THUMBING_S3_FOLDER_INPUT="avatar/original"
THUMBING_S3_FOLDER_OUTPUT="avatar/processed"
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