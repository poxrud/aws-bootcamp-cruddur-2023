# Week 5 — DynamoDB and Serverless Caching

## Implement Schema Load Script

Inside `backend-flask/bin` I crated three scripts:

- schema-load
- drop
- list-tables

_schma-load_ creates a dynamodb database with the schema required for our access patters.

```bash [backend-flask/bin/ddb/schema-load]
# backend-flask/bin/ddb/schema-load

#!/usr/bin/env python3

import boto3
import sys

attrs = {
  'endpoint_url': 'http://localhost:8000'
}

if len(sys.argv) == 2:
  if "prod" in sys.argv[1]:
    attrs = {}

ddb = boto3.client('dynamodb',**attrs)

table_name = 'cruddur-messages'

response = ddb.create_table(
  TableName=table_name,
  AttributeDefinitions=[
    {
      'AttributeName': 'pk',
      'AttributeType': 'S'
    },
    {
      'AttributeName': 'sk',
      'AttributeType': 'S'
    },
  ],
  KeySchema=[
    {
      'AttributeName': 'pk',
      'KeyType': 'HASH'
    },
    {
      'AttributeName': 'sk',
      'KeyType': 'RANGE'
    },
  ],
  #GlobalSecondaryIndexes=[
  #],
  BillingMode='PROVISIONED',
  ProvisionedThroughput={
      'ReadCapacityUnits': 5,
      'WriteCapacityUnits': 5
  }
)

print(response)
```

I then gave it `u+x` permissions and ran it:
![DDB Schema Load Script](/assets/ddb-schema-load.png)

I then validated that we have a new table with the `list-tables`
script.

```bash [backend-flask/bin/ddb/list-tables]
# backend-flask/bin/ddb/list-tables
#! /usr/bin/bash

if [ "$1" = "prod" ]; then
  echo "Running in production mode"
  ENDPOINT_URL=""
else
  ENDPOINT_URL="--endpoint-url=http://localhost:8000"
fi

aws dynamodb list-tables $ENDPOINT_URL \
--query TableNames \
--output table
```

Output:

![DDB List Tables](/assets/ddb-list-tables.png)

The `drop` script simply drops the provided table with the aws cli:

```bash
aws dynamodb delete-table $ENDPOINT_URL \
--table-name $TABLE_NAME
```

Output:

![DDB drop tables](/assets/ddb-drop.png)

## Implement Seed Script

The seed script is a file located in `backend-flask/bin/ddb/seed` and is used
to seed the database with a sample "message group" and multiple messages in that group.
You can view the seed file here:
https://github.com/poxrud/aws-bootcamp-cruddur-2023/blob/d2339bb780dbfd7bcc1d0276ffff96ac01ad5765/backend-flask/bin/ddb/seed

We can see the contents of the DynamoDB database after the seed, when we run the `scan` script.

## Implement Scan Script

Here are the contents of `backend-flask/bin/ddb/scan` used to display the contents of the DynamoDB "cruddur-messages" table.
This table has been seeded with a sample conversation.

```bash [backend-flask/bin/ddb/scan]
# backend-flask/bin/ddb/scan

import boto3

attrs = {
  'endpoint_url': 'http://localhost:8000'
}
ddb = boto3.resource('dynamodb', **attrs)
table_name = 'cruddur-messages'

table = ddb.Table(table_name)
response = table.scan()

items = response['Items']
for item in items:
  print(item)

```

Output:

![DDB scan](/assets/ddb-bin-scan.png)

## Implement Pattern Scripts for Read and List Conversations

Inside `backend-flask/bin/ddb/` we created a new directory called _patters_ which contains two files, for the listing of conversations, and getting a specific conversation. This supports two of our access patterns.

The two scripts in `backend-flask/bin/ddb/patterns` are:

- list-conversations
- get-conversation

### list-conversations

This script lists all the conversation for a specific handle,
currently hardcoded to 'andrewbrown', because that is what is used in our seed script.
The file is available here: https://github.com/poxrud/aws-bootcamp-cruddur-2023/blob/d2339bb780dbfd7bcc1d0276ffff96ac01ad5765/backend-flask/bin/ddb/patterns/list-conversations

Here is the output after giving the script u+x permissions and running it:
![list-conversations output](/assets/ddb-bin-list-conversations.png)

### get-conversation

This script gets a specific conversation, based on a `message_group_uuid`, and the year '2023'. This is currently hardcoded to a value that we previously seeded.
The script is available here: https://github.com/poxrud/aws-bootcamp-cruddur-2023/blob/d2339bb780dbfd7bcc1d0276ffff96ac01ad5765/backend-flask/bin/ddb/patterns/get-conversation

Output after running:

![Get conversation](/assets/ddb-bin-list-conversation.png)

## Implement Update Cognito ID Script for Postgres Database

- set env variable AWS_COGNITO_USER_POOL_ID to ca-central-1_PHdtNYjuS
  export AWS_COGNITO_USER_POOL_ID="ca-central-1_PHdtNYjuS"

```py
## bin/db/update_cognito_user_ids

import boto3
import os
import sys

print("== db-update-cognito-user-ids")

current_path = os.path.dirname(os.path.abspath(**file**))
parent_path = os.path.abspath(os.path.join(current_path, '..', '..'))
sys.path.append(parent_path)
from lib.db import db

def update_users_with_cognito_user_id(handle, sub):
sql = """
UPDATE public.users
SET cognito_user_id = %(sub)s
WHERE
users.handle = %(handle)s;
"""
db.query_commit(sql, {
'handle': handle,
'sub': sub
})

def get_cognito_user_ids():
userpool_id = os.getenv("AWS_COGNITO_USER_POOL_ID")
client = boto3.client('cognito-idp')
params = {
'UserPoolId': userpool_id,
'AttributesToGet': [
'preferred_username',
'sub'
]
}
response = client.list_users(\*\*params)
users = response['Users']
dict_users = {}
for user in users:
attrs = user['Attributes']
sub = next((a for a in attrs if a["Name"] == 'sub'), None)
handle = next(
(a for a in attrs if a["Name"] == 'preferred_username'), None)
dict_users[handle['Value']] = sub['Value']
return dict_users

users = get_cognito_user_ids()

for handle, sub in users.items():
print('----', handle, sub)
update_users_with_cognito_user_id(
handle=handle,
sub=sub
)

```

## Implement (Pattern A) Listing Messages in Message Group into Application

- I created a `/backend-flask/bin/cognito/list-users` script to be able to get a list of Cognitio users. I then created a new
  user using the Front-end with the name and handle of John Smith, johnsmith. In order to have a conversation we require at least
  two users.

![List Users](/assets/list-users-ddb.png)

I then changed the ddb seed data to make sure the conversation was between my handle and the @johnsmith handle.
After this I implemented the access pattern A with the results below:

![message-group-messages-hardcoded](/assets/message-group-messages-hardcoded.png)

I then changed the backend code to pull the messages from the ddb database, instead of returning the hardcoded ones.

![message-group-messages](/assets/message-group-messages.png)

## Implement (Pattern B) Listing Messages Group into Application

I did not have any issues with this implementation, as can be seed by the screenshot below. It shows
the current message groups for the @philoxrud user.

![cruddur-messages.png](/assets/cruddur-messages.png)

## Implement (Pattern C) Creating a Message for an existing Message Group into Application

After modifying the front-end and back-end to support Pattern C access, I was able to post new messages
into a current message group (conversation).

![New Message into existing Message Group](/assets/new-message.png)

## Implement (Pattern D) Creating a Message for a new Message Group into Application

After modifying the front-end and back-end to support Pattern D access, I was able to create new messages
that were part of a new message group (conversation). This is how you start a new conversation for the first time. This step also required the introduction of a new service called: `UsersShort`.
This service is a public api endpoint that provides basic information on a user _handle_.

![New Message into new Message Group](/assets/new-message-with-new-group.png)

## Implement (Pattern E) Updating a Message Group using DynamoDB Streams

- create DynamoDB on prod

```sh
$ bin/ddb/schema-load prod
{'TableDescription': {'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}, {'AttributeName': 'sk', 'AttributeType': 'S'}], 'TableName': 'cruddur-messages', 'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}], 'TableStatus': 'CREATING', 'CreationDateTime': datetime.datetime(2023, 4, 3, 14, 50, 38, 363000, tzinfo=tzlocal()), 'ProvisionedThroughput': {'NumberOfDecreasesToday': 0, 'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}, 'TableSizeBytes': 0, 'ItemCount': 0, 'TableArn': 'arn:aws:dynamodb:ca-central-1:632626636018:table/cruddur-messages', 'TableId': '12ad7550-87b1-4f5e-97f0-17aad96eba99', 'DeletionProtectionEnabled': False}, 'ResponseMetadata': {'RequestId': '5QN8GQUSSJ0HR0RK60H6VA5OR7VV4KQNSO5AEMVJF66Q9ASUAAJG', 'HTTPStatusCode': 200, 'HTTPHeaders': {'server': 'Server', 'date': 'Mon, 03 Apr 2023 14:50:38 GMT', 'content-type': 'application/x-amz-json-1.0', 'content-length': '613', 'connection': 'keep-alive', 'x-amzn-requestid': '5QN8GQUSSJ0HR0RK60H6VA5OR7VV4KQNSO5AEMVJF66Q9ASUAAJG', 'x-amz-crc32': '2611804563'}, 'RetryAttempts': 0}}
```

- in docker-compose.yml , in the `backend-flask` section, comment out the AWS endpoint to point our app to production DynamoDB

```yml
# AWS_ENDPOINT_URL: "http://dynamodb-local:8000"
```

Then using the AWS Console turn on DynamoDB streams with the _New Image_ type.

![DynamoDB Streams Setup](/assets/dynamodb-stream-setup.png)
![DynamoDB Streams Running](/assets/dynamodb-stream-setup2.png)

In order for Lambda to be able to access DynamoDB securely we need to create a _Gateway Endpoint_.
We do this using the AWS Console.

![DynamoDB Gateway Endpoint](/assets/dynamodb-vpc-gateway-endpoint.png)

Next we need to create a Lambda that will run on the DynamoDB stream trigger and assign it the correct permissions.
The Lambda code is below:

```py
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource(
 'dynamodb',
 region_name='ca-central-1',
 endpoint_url="http://dynamodb.ca-central-1.amazonaws.com"
)

def lambda_handler(event, context):
  print('event-data',event)

  eventName = event['Records'][0]['eventName']
  if (eventName == 'REMOVE'):
    print("skip REMOVE event")
    return
  pk = event['Records'][0]['dynamodb']['Keys']['pk']['S']
  sk = event['Records'][0]['dynamodb']['Keys']['sk']['S']
  if pk.startswith('MSG#'):
    group_uuid = pk.replace("MSG#","")
    message = event['Records'][0]['dynamodb']['NewImage']['message']['S']
    print("GRUP ===>",group_uuid,message)

    table_name = 'cruddur-messages'
    index_name = 'message-group-sk-index'
    table = dynamodb.Table(table_name)
    data = table.query(
      IndexName=index_name,
      KeyConditionExpression=Key('message_group_uuid').eq(group_uuid)
    )
    print("RESP ===>",data['Items'])

    # recreate the message group rows with new SK value
    for i in data['Items']:
      delete_item = table.delete_item(Key={'pk': i['pk'], 'sk': i['sk']})
      print("DELETE ===>",delete_item)

      response = table.put_item(
        Item={
          'pk': i['pk'],
          'sk': sk,
          'message_group_uuid':i['message_group_uuid'],
          'message':message,
          'user_display_name': i['user_display_name'],
          'user_handle': i['user_handle'],
          'user_uuid': i['user_uuid']
        }
      )
      print("CREATE ===>",response)
```

We create a trigger for the Lambda above:

![Lambda Trigger](/assets/dynamodb-lambda-trigger-setup.png)
![Lambda Trigger2](/assets/dynamodb-lambda-trigger.png)

And assign an IAM role to the Lambda

![Lambda role](/assets/dynamodb-basic-lambda-role.png)

I then used the front-end to send a message

![cruddur new message](/assets/cruddur-new-message-with-dynamodb-stream.png)

This worked but when checking CloudWatch Logs a permissions error was discovered.

![dynamodb error](/assets/dynamodb-lambda-trigger-permissions-error.png)

The solutions is to attach an inline policy with proper permissions to the Lambda

- inside /AWS/policies/cruddur-messaging-stream-policy.json

```json
}
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:ca-central-1:632626636018:table/cruddur-messages/index/message-group-sk-index",
                "arn:aws:dynamodb:ca-central-1:632626636018:table/cruddur-messages"
            ]
        }
    ]
```

This solved the errors.

![DynamoDB streams no errors](/assets/dynamodb-lambda-trigger-permissions-no-errors.png)
