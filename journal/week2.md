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

## Instrument Honeycomb with OTEL

I followed the week2 instructions [here](https://github.com/omenking/aws-bootcamp-cruddur-2023/blob/week-2/journal/week2.md) and did not have any issues implementing Honeycomb.

To summarize I did the following steps:

- added opentelemetry libs to requirements.txt and installed them
- added the OTEL middleware to `app.py` in `/backend-flask`
- added reference to the two HONEYCOMB related envronmental variables to docker-compose.yml
- set the values for the env variables using gitpod's `gp env` command

Here are some screenshots of honeycomb successfully receiving spans:
![honeycomb1](/assets/honeycomb1.png)
![honeycomb2](/assets/honeycomb2.png)

and here is an email that I received from honeycomb, confirming that they have created
a new dataset based on the incoming data.

![honeycomb-dataset](/assets/honeycomb-email.png)

## Configure custom logger to send to CloudWatch Logs

I followed the week2 instructions and did not have any issues implementing
CloudWatch Logs into the backend-flask application.

NOTE: In order to reuse the same Logger instance throughout my application and
without having to pass it around as an argument, I created a logger.py module.
I placed the module inside the `backend-fask/utils` directory.

This is the contents of the logger module:

```python
import watchtower
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
cw_handler = watchtower.CloudWatchLogHandler(log_group='cruddur')
LOGGER.addHandler(console_handler)
LOGGER.addHandler(cw_handler)
```

Then whenever I need to use the logger I can simply import it and use it
directly.

```python
from utils.logger import LOGGER
LOGGER.info("HomeActivities")
```

After setting the region and API keys in docker-compose.yml and running `docker-compose up`
I was able to get some logs from CWLogs.

Here is a screenshot of my CWLogs Log Group:
![Crudder Log Group](/assets/crudder-log-group.png)

Here are logs being sent to the Crudder log group
![Crudder Log Stream](/assets/crudder-log-stream.png)

And here is a custom log message "HomeActivities" being sent from the `/api/activities/home` API endpoint
![HomeActivities-logs](/assets/HomeActivities-logs.png)

## Integrate Rollbar and capture an error

I successfully integrated Rollbar and captured an error by hitting an incorrect api endpoint.

To test of sending a custom message to rollbar I added a new API endpoint to the
bottom of app.py file with the following code:

```python
...

# Rollbar test path ------------
@app.route('/rollbar/test')
def rollbar_test():
    rollbar.report_message('Hello World!', 'warning')
    return "Hello World!"

if __name__ == "__main__":
  app.run(debug=True)
```

I then visited the API endpoint `/api/rollbar/test` and checked the Rollbar UI to see if data
was sent.

Here you can see that Rollbar received the _Hello World_ message.
![rollbar-helloworld](/assets/rollbar-helloworld.png)

The second part of the homework required us to capture an application error
with rollbar.

I forced an error by visiting an invalid API endpoint, specifically:

```
/api/activities/home2
```

This created a `NameError`.

Here is a screenshot of the Rollbar UI where the NameError stacktrace is captured:

![rollbar-error-capture](/assets/rollbar-error-capture.png)

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

## Add custom instrumentation to Honeycomb to add more attributes and a custom span

I added a custom span called `home-activities-mock-data` to the `/api/activities/home` endpoint inside the `/services/home_activities.py` file.

First we import the opentelemetry tracer with

```python
from opentelemetry import trace
tracer = trace.get_tracer("home-activities")
```

then inside the `run()` function we wrap the code in a block that will create
our span.

```python
class HomeActivities:
  def run():

    with tracer.start_as_current_span("home-activities-mock-data"):
      now = datetime.now(timezone.utc).astimezone()
      results = [{
        ...
      }]
    return results
```

As you can see in the screenshot this was enough to create our custom span.

![custom span](/assets/custom-span.png)

The second part of the requirement was to add some custom attributes to our new span.
I added two new attributes: `userId` and `now`.

I added the code below at the end of the `run()` function referenced above.

```python
  ...

  span = trace.get_current_span()
  span.set_attribute("app.userId", 1001)
  span.set_attribute("app.now", now.isoformat())
  return results
```

The code creates an `app.userId` and `app.now` custom attributes to be sent to Honeycomb,
under the current active span.

Here is our custom attributes appearing in Honeycomb.

![custom attribute](/assets/honeycomb-custom-attribute.png)

## Run custom queries in Honeycomb and save them later eg. Latency by UserID, Recent Traces

I wanted to run a custom query that would be useful in a real world scenario.
For example:
"Find all of our URL's that require a logged in user, that have a large latency (above 50ms)".

This type of a query could potentially find slow pages and as a result improve the user experience of our site.

Here is how the above query was created using Honeycomb's UI:

![honeycomb-query](/assets/honeycomb-custom-query.png)

I was able to find and execute the query at a later time using the _My History_ page:

![Query History](/assets/honeycomb-query-history.png)

## Instrument Honeycomb for the frontend-application to observe network latency between frontend and backend

I was able to add front-end instrumentation to my react app by utilizing this guide:
[Link](https://docs.honeycomb.io/getting-data-in/opentelemetry/browser-js/).
For simplicity I used the insecure method of embedding my honeycomb API key directly into the web app and sent the traces from the browser direct to honeycomb.

As you can see in the screenshots below I was able to create a new "browser" dataset and send web browser tracing data to honeycomb:

![browser dataset](/assets/browser-dataset.png)
![honeycomb http get trace](/assets/honeycomb-HTTP-GET-trace.png)

### Tie Front-end and Backend to determine latency

Unfortunately due to what I believe could be an issue with honeycomb's backend I was unable
to tie the web trace requests with my backened.

Even though I confirmed with DevTools that my browser is sending the correct data,
honeycomb UI did not set the "traceId" correctly. I have opened a support ticket
with honeycomb and am hoping to resolve this issue.

Here is my browser sending the correct data:
![Screenshot ConsoleSpanExporter](/assets/Screenshot-ConsoleSpanExporter.png)
Here is the error in Honeycomb when tying the frontend to backend:
![honeycomb error](/assets/honeycomb-error.png)
Here is the open support ticket:
![honeycomb support ticket](/assets/honeycomb-support.png)
