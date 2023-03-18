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
