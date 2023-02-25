# Week 1 — App Containerization

## Remember to Commit Your Code
I committed all my code to *week1* branch and them merged it into main when all homework was completed.

## Containerize Application (Dockerfiles, Docker Compose)
I created the docker files for:
- Flask backend
- React Frontend
The dockerfile's and docker-composed can be found in my repo.

Here is evidence of the docker images running:

![docker images](/assets/dockerized-applications.png)

## Document the Notification Endpoint for the OpenAI Document
I inserted the following path into the `openapi-3.0.yml` file.

```yml
/api/activities/notifications:
    get:
      description: 'Return a feed of users that we follow'
      tags:
        - activities
      parameters: []
      responses:
        '200':
          description: Returns an array of activities
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Activity'
```

## Write a Flask Backend Endpoint for Notifications
I added a new service called `NotificationsActivities`, and a new notifications API path in App.py.
Here is evidence of a successful /api/activities/notifications response.

![Notifications Activities](/assets/notifications-activities.png)

## Write a React Page for Notifications
Created a new React Page components to display activity notifications.
Here is evidence of a succfull display of activity notifications.

![Notifications Activities](/assets/react-notifications.png)

## Run DynamoDB Local Container and ensure it works
Here is evidence of me running a query on a running DynamoDB container.
![DynamoDB](/assets/dynamodb.png)

## Run Postgres Container and ensure it works
Here is evidence of me running a query on a running DynamoDB container.
![Postgresql](/assets/postgresql.png)

