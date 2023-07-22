# Week X

```sh
bin/frontend/static-build
```

- create /erb/sybc.env.erb
- create /bin/frontend/sync
- create /tmp/.keep

```sh
bin/frontend/generate-env 
```

```
gem install aws_s3_website_sync
gem install dotenv
```

```sh
bin/frontend/sync
```

- run rds schema load and migrations

- setup s3 custom error page forwarding to make SPA's work
```yml
CustomErrorResponses:
          - ErrorCode: 403
            ResponseCode: 200
            ResponsePagePath: /index.html
```

- put cognito cruddur-post-confirmation lambda into our private VPC
- create SG CognitoLambdaSG, and add it as incoming source in RDS SG

- CloudFormation Service fix CORS
  - edit service/template.yaml and service/config.toml with
  ```yml
  EnvFrontendUrl = 'https://mycruddur.net'
  EnvBackendUrl = 'https://api.mycruddur.net'
  ```

  - deploy  with bin/cfn/service

  - fix POST route for /api/activities, remove the hardcoded username
  - fix activity form to not be hardcoded in ActivityForm.js

## Ensure CI/CD pipeline works and create activity works
- fixed cicd template.yml and the nested codebuild.yaml
- did a PR for prod
- checked pipeline
- build frontend and run `sync` tool
- verify changes on www.mycruddur.net

## Refactor to use JWT Decorator in Flask App
- using my JWT sidecar, and the decorator below
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
- refactored routes, and other things

## Implement Replies
- fix frontend for sending auth token
- created CreateReply.py class
- created new reply.sql
- created new migration for changing `reply_to_activity_uuid` type from `integer` to `uuid`
  - this required fixing a bug in migration script in the creation of timestamps. Sometimes the crated timestamps were incorrect because of dropping of the decimal parts of the timestamp. The solution was to generate the migration timestamp with the following code:
  ```python
     timestamp = int(datetime.now(timezone.utc).timestamp())
  ```
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
- fix CSS so that replies are off to the right of the parent message

## Improved Error Handling for the app

- move the activities json array from home.sql to show.sql
- modify ReplyForm.js and ActivityForm to show errors
  - do this by adding FormErrors.js and FormErrorItem.js components and their css
- add better errors to Signup and Signin Page using `<FormErrors/>` component

- refactor post, put, get, delete into lib/Requests.js and update our forms.
  - The following files were refactored with the new `post` and `get`methods:
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

- In ActivityContent.js make only name and photo clickable 
- Create ActivityShowPage.js page and css
- Add User status route to show user activities.
  - in backend-flask/routes/users.py

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

  - In react-frontend create ActivityShowPage and associated components and styling to show all the replies to a specific activities. 
 
 # More General Cleanup Part 1 and Part 2

 - run migration on prod
 ```sh
 CONNECTION_URL=$PROD_CONNECTION_URL bin/db/migrate
 ```

 - update backend and frontend on production
  - for backend merge week-x into prod and check CodePipeline for success
  - for frontend:
    - run `bin/frontend/static-build`
    - rub `bin/frontend/sync`

- fix DynamoDB connection to use env vars for table name and DynamoDB endpoint url. 
  - edit backend-flask.env.erb
  - edit aws/cfn/service/template.yaml  and config.toml
  - deploy to cloudformation and execute changeset

- create a machine user for DynamoDB access using CloudFormation
  - deploy using bin/cfn/machineuser
      

EXTRA CREDIT

- setup Github Actions for pushes to Prod, to build frontend and sync it

- fixed root domain forwarding to www forwarding
