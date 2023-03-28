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
