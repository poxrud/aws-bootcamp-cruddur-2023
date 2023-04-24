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