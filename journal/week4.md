# Week 4 — Postgres and RDS

## Create RDS Postgres Instance

I used the AWS ClI to run the following command:

```sh
aws rds create-db-instance \
  --db-instance-identifier cruddur-db-instance \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version  14.6 \
  --master-username cruddurroot \
  --master-user-password <secret> \
  --allocated-storage 20 \
  --availability-zone ca-central-1a \
  --backup-retention-period 0 \
  --port 5432 \
  --no-multi-az \
  --db-name cruddur \
  --storage-type gp3 \
  --publicly-accessible \
  --storage-encrypted \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --no-deletion-protection
```

This created an RDS database called `crudder-db-instance` with the username of
`crudderroot`.

![crudder RDS instance](/assets/crudder-rds-instance.png)

## Bash scripting for common database actions

Inside backend-flask directory, make a new directory called db.

```sh
cd backend-flash
mkdir db
cd db
```

Inside _db_ make a new file called `schema.sql` with the following content:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.activities;
CREATE TABLE public.users (
  uuid UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  display_name text,
  handle text,
  cognito_user_id text,
  created_at TIMESTAMP default current_timestamp NOT NULL
);
CREATE TABLE public.activities (
  uuid UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_uuid UUID NOT NULL,
  message text NOT NULL,
  replies_count integer DEFAULT 0,
  reposts_count integer DEFAULT 0,
  likes_count integer DEFAULT 0,
  reply_to_activity_uuid integer,
  expires_at TIMESTAMP,
  created_at TIMESTAMP default current_timestamp NOT NULL
);
```

This will be run later by the `db-schema-load` script to load the schema.

Create `seed.sql` inside the `backend-flask/db` directory with the following content:

```sql
-- this file was manually created
INSERT INTO
  public.users (display_name, handle, cognito_user_id)
VALUES
  ('Andrew Brown', 'andrewbrown', 'MOCK'),
  ('Andrew Bayko', 'bayko', 'MOCK');

INSERT INTO
  public.activities (user_uuid, message, expires_at)
VALUES
  (
    (
      SELECT
        uuid
      from
        public.users
      WHERE
        users.handle = 'andrewbrown'
      LIMIT
        1
    ),
    'This was imported as seed data!',
    current_timestamp + interval '10 day'
  )
```

This will be later used by the `bin/db-seed` file to seed our db with some mock data.

Inside `/backend-flask` make a new folder called `bin`.

Inside `bin` create 7 new files:

- db-create
- db-drop
- db-schema-load
- db-connect
- db-seed
- db-sessions
- db-setup

The files need to be made executable with the following command:

```sh
chmod u+x db-create
chmod u+x db-drop
chmod u+x db-schema-load
chmod u+x db-connect
chmod u+x db-seed
chmod u+x db-sessions
chmod u+x db-setup
```

![bin-scripts permissions](/assets/bin-scripts.png)

Here are the contents of the scripts inside `backend-flask/bin`:

```sh
## db-create

#! /usr/bin/bash

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="db-create"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

NO_DB_CONNECTION_URL=$(sed 's/\/cruddur//g' <<<"$CONNECTION_URL")
psql ${NO_DB_CONNECTION_URL} -c "create database cruddur;"
```

```sh
## db-drop

#! /usr/bin/bash

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="db-drop"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

NO_DB_CONNECTION_URL=$(sed 's/\/cruddur//g' <<<"$CONNECTION_URL")
psql $NO_DB_CONNECTION_URL -c "drop database if exists cruddur;"
```

```sh
## db-schema-load
#! /usr/bin/bash

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="db-schema-load"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

schema_path="$(realpath .)/db/schema.sql"

if [ "$1" = "prod" ]; then
  echo "Running in production mode"
  URL=$PROD_CONNECTION_URL
else
  URL=$CONNECTION_URL
fi

psql $URL cruddur < $schema_path
```

```sh
## db-connect
#! /usr/bin/bash

psql $CONNECTION_URL
```

```sh
## db-sessions
#! /usr/bin/bash

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="db-sessions"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

if [ "$1" = "prod" ]; then
  echo "Running in production mode"
  URL=$PROD_CONNECTION_URL
else
  URL=$CONNECTION_URL
fi

NO_DB_URL=$(sed 's/\/cruddur//g' <<<"$URL")
psql $NO_DB_URL -c "select pid as process_id, \
       usename as user,  \
       datname as db, \
       client_addr, \
       application_name as app,\
       state \
from pg_stat_activity;"
```

```sh
## db-setup
#! /usr/bin/bash
set -e # stop if it fails at any point

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="db-setup"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

bin_path="$(realpath .)/bin"

source "$bin_path/db-drop"
source "$bin_path/db-create"
source "$bin_path/db-schema-load"
source "$bin_path/db-seed"
```

For the scripts to work I had to set the following env variables:

```sh
export CONNECTION_URL="postgres://postgres:password@localhost:5432/cruddur"
export PROD_CONNECTION_URL="postgres://crudderroot:<secret>@cruddur-db-instance.cps1z2xv6o2y.ca-central-1.rds.amazonaws.com:5432/crudder"
```

I got the prod connection endpoint from the AWS console:

![rds connection endpoint](/assets/rds-connect-endpoint.png)

Here is `bin/db-setup` running, creating our database, loading schema, and seeding data.

![db-setup script](/assets/db-setup-script.png)

Here is the `db-sessions` script showing the running postgres sessions:

![db sesions](/assets/db-sessions.png)

## Install Postgres Driver in Backend Application

Inside `/backend-flask/lib` I added `db.py` with the following content:

```py
from psycopg_pool import ConnectionPool
import os

connection_url = os.getenv("CONNECTION_URL")
pool = ConnectionPool(connection_url)

def query_wrap_object(template):
  sql = f"""
  (SELECT COALESCE(row_to_json(object_row),'{{}}'::json) FROM (
  {template}
  ) object_row);
  """
  return sql

def query_wrap_array(template):
  sql = f"""
  (SELECT COALESCE(array_to_json(array_agg(row_to_json(array_row))),'[]'::json) FROM (
  {template}
  ) array_row);
  """

  return sql
```

I then changed `backend-flask/services/home_activities` to include the following code at the bottom of the `run()` function, instead of the previous mock data.

```py
...

sql = query_wrap_array("""
      SELECT
        activities.uuid,
        users.display_name,
        users.handle,
        activities.message,
        activities.replies_count,
        activities.reposts_count,
        activities.likes_count,
        activities.reply_to_activity_uuid,
        activities.expires_at,
        activities.created_at
      FROM public.activities
      LEFT JOIN public.users ON users.uuid = activities.user_uuid
      ORDER BY activities.created_at DESC
      """)

      with pool.connection() as conn:
        with conn.cursor() as cur:
          cur.execute(sql)
          # this will return a tuple
          # the first field being the data
          json = cur.fetchone()

      return json[0]
  ...
```

Here is the front-end running when the backend is using the new Postgres driver:

!["Postgres connector"](/assets/postgresql-connector.png)

## Connect Gitpod to RDS Instance

First I found out gitpod's local IP address, and set it to the environmental variable GITPOD_IP:

![gitpod ip](/assets/GITPOD-IP.png)
![gitpod ip env set](/assets/GITPOD_IP2.png)

I logged into AWS Console and started up my RDS instance,
followed by configuring the **inbound** security group rules.

![RDS Security Group](/assets/rds-sg.png)

To test the connection I executed:

```sh
psql $PROD_CONNECTION_URL
```

and was successfully connected to RDS.

![RDS Connect Test](/assets/rds-connect-test.png)

Finally, I created the schema on RDS:

![RDS Schema Script](/assets/rds-setup-script.png)

In order to make sure the security group gets updated on every gitpod launch I followed the following steps:

- create `backend-flask/bin/rds-update-sg-rule` with:

```sh
#! /usr/bin/bash

CYAN='\033[1;36m'
NO_COLOR='\033[0m'
LABEL="rds-update-sg-rule"
printf "${CYAN}== ${LABEL}${NO_COLOR}\n"

aws ec2 modify-security-group-rules \
 --group-id $DB_SG_ID \
 --security-group-rules "SecurityGroupRuleId=$DB_SG_RULE_ID,SecurityGroupRule={Description="GITPOD",IpProtocol=tcp,FromPort=5432,ToPort=5432,CidrIpv4=$GITPOD_IP/32}"
```

![Update security group script](/assets/rds-update-sg.png)

- edit `.gitpod.yml` and add the following to the bottom:

```yml
command: |
  export GITPOD_IP=$(curl ifconfig.me)
  source "$THEIA_WORKSPACE_ROOT"/backend-flask/bin/rds-update-sg-rule
```

## Create AWS Cognito trigger to insert user into database

Using the code below I created a lambda function to run every time a new user is created using Cognito.

```py
# AWS/lambdas/cruddur-post-confirmation.py
import json
import psycopg2
import os


def lambda_handler(event, context):
  user = event['request']['userAttributes']

  user_display_name = user['name']
  user_handle = user['preferred_username']
  user_email = user['email']
  user_cognito_id = user['sub']

  try:
    conn = psycopg2.connect(os.getenv('CONNECTION_URL'))
    cur = conn.cursor()

    sql = f"""
    INSERT INTO public.users (display_name, handle, email, cognito_user_id)
    VALUES(%s, %s, %s, %s)
    """

    params = [
      user_display_name,
      user_handle,
      user_email,
      user_cognito_id
    ]

    cur.execute(sql, *params)
    conn.commit()

  except (Exception, psycopg2.DatabaseError) as error:
    print(error)

  finally:
    if conn is not None:
      cur.close()
      conn.close()
      print('Database connection closed.')

  return event
```

Here it is on AWS Console

![crudder-post-confirmation](/assets/crudder-post-confirmation.png)

Here it is setup to run as a Cognito trigger:

![crudder-lambda-trigger](/assets/crudder-lambda-trigger.png)

The lambda function needs to run inside the same VPC that RDS is in. To do this it needs
permissions to be able to add/remove EC2 Network Interfaces so that it could connect to the VPC.

I created an inline policy to get Lambda these permissions. Here is the policy:

```json
// LambdaVPCAccess
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
```

Once the permissions were setup I assigned the Lambda to the same VPC as RDS and then gave it the same security group.

In order for the Lambda to be able to connect the RDS they need to have the same security group. This works because of self referencing SG's.

![lambda same vpc and sg](/assets/lambda-vpc-with-sg.png)

Finally, I used the front end to create a new user, confirmed it, and then checked RDS to see if the user
was added successfully.

![cognito new user in RDS](/assets/cognito-user-in-rds.png)

# Create new activities with a database insert

I first changed `docker-compose.yml` to point the backend to RDS instead of our local db.

```yml
# CONNECTION_URL: "postgres://postgres:password@db:5432/cruddur"
CONNECTION_URL: "${PROD_CONNECTION_URL}"
```

Then based on **omenking**'s _week-4-again_ github repo, and the youtube video [Week 4 - Creating Activities](https://www.youtube.com/watch?v=fTksxEQExL4&list=PLBfufR7vyJJ7k25byhRXJldB5AiwgNnWv&index=49)
I created the following files.

- backend-flask/db/sql/activities/create.sql
- backend-flask/db/sql/activities/home.sql
- backend-flask/db/sql/activities/object.sql

These are SQL templates to be used by `backend-flask/lib/db.py`. This file was copied and modified from omenking's repo.

I then modified `services/create_activity.py` to use the new db.py in order to create a Cruddur activity.

```py
#services/create_activity.py

# ...

if model['errors']:
      model['data'] = {
        'handle': user_handle,
        'message': message
      }
    else:
      expires_at = (now + ttl_offset)
      uuid = CreateActivity.create_activity(user_handle, message, expires_at)

      object_json = CreateActivity.query_object_activity(uuid)
      model['data'] = object_json

    return model

def create_activity(handle, message, expires_at):
    sql = db.template('activities', 'create')
    uuid = db.query_commit(sql, {
      'handle': handle,
      'message': message,
      'expires_at': expires_at
    })
    return uuid

  def query_object_activity(uuid):
    sql = db.template('activities', 'object')
    return db.query_object_json(sql, {
      'uuid': uuid
    })
```

To make things work two more changes were required.

- modify `services/home_activities.py` to use the new SQL templating class
- modify `app.py` and change the hardcoded `andrewbrown` handle to hardcoded `philoxrud` handle

After the changes I tested the changes in the front end by creating a new activity.

![New Activity](/assets/new_activity1.png)

![New Activity2](/assets/new_activity2.png)

![New Activity3](/assets/new_activity3.png)
