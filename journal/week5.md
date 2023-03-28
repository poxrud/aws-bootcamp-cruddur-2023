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

## Implement Scan Script

## Implement Pattern Scripts for Read and List Conversations
