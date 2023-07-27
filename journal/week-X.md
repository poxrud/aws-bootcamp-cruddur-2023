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

- setup Github Actions for pushes to Prod, to build frontend and sync it

- fixed root domain forwarding to www forwarding
