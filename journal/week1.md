# Week 1 — App Containerization

## Remember to Commit Your Code
I committed all my code to *week1* branch and them merged it into main when all homework was completed.

## Containerize Application (Dockerfiles, Docker Compose)
I created the docker files for:
- Flask backend
- React Frontend

The dockerfiles and docker-compose can be found in my repo.

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
Created a new React page component to display activity notifications.
Here is evidence of a succefull display of activity notifications.

![Notifications Activities](/assets/react-notifications.png)

## Run DynamoDB Local Container and ensure it works
Here is evidence of me running a query on a running DynamoDB container.
![DynamoDB](/assets/dynamodb.png)

## Run Postgres Container and ensure it works
Here is evidence of me connecting to PostgreSQL using Database Explorer
![Postgresql](/assets/postgresql.png)

# Homework Challenges

## Run the dockerfile CMD as an external script
I created a bash script called `run_flask.sh`
with the following code inside:

```bash
#!/bin/bash
python3 -m flask run --host=0.0.0.0 --port=4567
```
I then gave it executable permissions and ran it:

```bash
chmod +x run_flask.sh
./run_flask.sh
```

You can see it run below:
![Docker CMD](/assets/docker-CMD.png)

## Push and tag a image to DockerHub
- I created a dockerhub free account.
- I build the flask docker image and then tagged it using the command:
`docker tag backend-flask poxrud/backendv1`

- I then pushed it to dockerhub with:
`docker push poxrud/backendv1:latest`

Here is a screenshot of my docker image on dockerhub:
![dockerhub image](/assets/dockerhub.png)

## Implement a healthcheck in the V3 Docker compose file
Added a healthcheck to the Postgres db service. 
Made the flask backend depend on the postgres healthcheck

Healthcheck:

```yml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

here is flask-backend depending on the service:

```yml
depends_on:
  db:
    condition: service_healthy
```

## Learn how to install Docker on your localmachine and get the same containers running outside of Gitpod / Codespaces
I installed *docker-desktop* on my mac and then cloned this repo on my local
machine with `git clone https://github.com/poxrud/aws-bootcamp-cruddur-2023`

I then entered the `frontend-react-js` and ran `npm i`.

When it completed I went back to the previous directory and ran docker-compose with:
`docker-compose up`. 

Here is the screenshot of the images running successfully on my local machine:
![docker-desktop](/assets/docker-desktop.png)