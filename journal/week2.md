# Week 2 — Distributed Tracing

## Instrument AWS X-Ray

I followed the instructions by doing the following:

- set my AWS_REGION environmental varible to "ca-central-1" (I'm also in Canada), and made sure they would persist in gitpod by using the `gp env` command
- added `aws-xray-sdk` to requiments.txt, and installed the python dependencies using pip
- created and `aws/json/xray.json` file for the sampling rules and enabled them using the
  `aws xray create-sampling-rule` command
- installed a local X-Ray daemon with dpkg
- added the X-Ray daemon to my `docker-compose.yml` file and added the required `AWS_XRAY_URL` and `AWS_XRAY_DAEMON_ADDRESS` environment variables to the docker-compose.yml file as well

It was then time to add the X-Ray code to the python flask-backend app and run the docker-compose up command.

I added the following code `backend-flask\app\app.py`:

```python
...
...
# AWS X-RAY --------------
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
xray_url = os.getenv("AWS_XRAY_URL")
xray_recorder.configure(service='backend-flask', dynamic_naming=xray_url)

...
...
app = Flask(__name__)

# AWS X-RAY -------------
XRayMiddleware(app, xray_recorder)
```

I then ran `docker-compose up` and tested X-Ray traces by hitting my front-end.
As you can see below, the AWS X-Ray was able to successfully receive the traces from
my backend.

![xray trace](/assets/xray-trace.png)

# Homework Challenges

## Create an X-Ray Subsegment

I created a subsegment called "activites-notifications" for the `/api/activities/notifications` api endpoint.

Inside the subsegment I added metadata that contained the response from the API call.

To add the subsegment I used the instructions from the `aws-xray-sdk-python` docs,
available here: [https://github.com/aws/aws-xray-sdk-python](https://github.com/aws/aws-xray-sdk-python)

To implement this I added the following code to the `backend-flask/services/notifications_activities.py` file:

First we import the xray_recorder at the top of the file.

```python
  from aws_xray_sdk.core import xray_recorder
```

Then inside the `run()` function:

```python
  subsegment = xray_recorder.begin_subsegment('activites-notifications')
  subsegment.put_metadata('results', results, 'activities/notifications')
  xray_recorder.end_subsegment()
```

Here you can see our subsegment `activities-notifications` being captured by X-Ray
![notification-subsegment](/assets/notification-subsegment.png)

and here is the metadata containing our `result`
![notifications-subsegment-raw](/assets/notifications-subsegment-raw.png)
