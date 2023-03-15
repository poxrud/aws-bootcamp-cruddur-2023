# Week 3 — Decentralized Authentication

## Setup Cognito User Pool

Using the AWS Console I created a Cognito user pool called _crudder-user-pool_.
I then used the console to create a new user and verify it using the AWS CLI.

![crudder user pool](/assets/crudder-user-pool.png)
![crudder user](/assets/crudder-user.png)

## Implement Custom Signin Page and Confirmation Page

Following the week3 instructions on github/omenking's journal and the live stream I npm installed
the Amplify library and imported it into the front-end project, into the App.js file.

```js
import { Amplify } from 'aws-amplify';

...

Amplify.configure({
  "aws_project_region": process.env.REACT_AWS_PROJECT_REGION,
  "aws_cognito_region": process.env.REACT_APP_AWS_COGNITO_REGION,
  "aws_user_pools_id": process.env.REACT_APP_AWS_USER_POOLS_ID,
  "aws_user_pools_web_client_id": process.env.REACT_APP_WEB_CLIENT_ID,
  "oauth": {},
  Auth: {
    region: process.env.REACT_AWS_PROJECT_REGION,           // REQUIRED - Amazon Cognito Region
    userPoolId: process.env.REACT_APP_AWS_USER_POOLS_ID,         // OPTIONAL - Amazon Cognito User Pool ID
    userPoolWebClientId: process.env.REACT_APP_WEB_CLIENT_ID,   // OPTIONAL - Amazon Cognito Web Client ID (26-char alphanumeric string)
  }
});
```

I made sure that I had the above env variables in my docker-compose file.

Once Auth from Amplify was configured, I modified `HomePageFeed.js` to show different versions of the UI based
on whether the user is logged in or not. This involved creating a `checkAuth` function shown below. The function gets an
authenticated user, or null (if not authenticated), and passes that information to the sidebar and the main navigation.

```js
// check if we are authenicated
const checkAuth = async () => {
  Auth.currentAuthenticatedUser({
    // Optional, By default is false.
    // If set to true, this call will send a
    // request to Cognito to get the latest user data
    bypassCache: false
  })
    .then((cognito_user) => {
      setUser({
        display_name: cognito_user.attributes.name,
        handle: cognito_user.attributes.preferred_username
      });
    })
    .catch((err) => {
      console.log(err);
    });
};
```

The `DesktopSidebar.js` also needed to be modified to show different UI based on the user's logged in/out state.

```js
let trending;
let suggested;
let join;
if (props.user) {
  trending = <TrendingSection trendings={trendings} />;
  suggested = <SuggestedUsersSection users={users} />;
} else {
  join = <JoinSection />;
}
```

To create a custom SignIn page I needed to modify the file `/frontend-react-js/src/pages/SigninPage.js`.
The modification consisted of importing Amplify and then replacing the original `onsubmit` function
with my version, shown below:

```js
const onsubmit = async (event) => {
  setErrors("");
  event.preventDefault();
  try {
    const user = await Auth.signIn(email, password);
    localStorage.setItem(
      "access_token",
      user.signInUserSession.accessToken.jwtToken
    );
    window.location.href = "/";
  } catch (error) {
    console.log("Error!", error.name);
    if (error.code == "UserNotConfirmedException") {
      window.location.href = "/confirm";
    }
    setErrors(error.message);
  }
  return false;
};
```

The abode code uses Amplify to confirm the sign in. If successful it saves the authentication token from Cognito
into localStorage. If the user exists but has not yet confirmed their email, the user will be redirected to
a `/confirm` page.

Therefore we require modifications to `/frontend-react-js/src/pages/ConfirmationPage.js`

We replace `onsubmit` with calls to Cognito:

```js
//src/pages/ConfirmationPage.js
const onsubmit = async (event) => {
  event.preventDefault();
  setErrors("");
  try {
    await Auth.confirmSignUp(email, code);
    window.location.href = "/";
  } catch (error) {
    setErrors(error.message);
  }
  return false;
};
```

We create a `resend_code()` function that will be responsible for sending a new confirmation code, in case
the previous one did not arrive.

```js
const resend_code = async (event) => {
  setCognitoErrors("");
  try {
    await Auth.resendSignUp(email);
    console.log("code resent successfully");
    setCodeSent(true);
  } catch (err) {
    // does not return a code
    // does cognito always return english
    // for this to be an okay match?
    console.log(err);
    if (err.message == "Username cannot be empty") {
      setErrors(
        "You need to provide an email in order to send Resend Activiation Code"
      );
    } else if (err.message == "Username/client id combination not found.") {
      setErrors("Email is invalid or cannot be found.");
    }
  }
};
```

We show different information, depending on whether the user requested a code to be resent or not with:

```js
let code_button;
if (codeSent) {
  code_button = (
    <div className="sent-message">
      A new activation code has been sent to your email
    </div>
  );
} else {
  code_button = (
    <button className="resend" onClick={resend_code}>
      Resend Activation Code
    </button>
  );
}
```

Here is a resent email confirmation:

![Email Confirmation Code](/assets/email-confirmation.png)

Here is a modified confirmation page :

![Email Confirmation Code](/assets/email-confirmation2.png)

## Implement Custom Signup Page

Just like with the above, to create a Signup Page I needed to change the onsubmit function in the `src/pages/Signup.js` file.

```js
const onsubmit = async (event) => {
  event.preventDefault();
  setErrors("");
  try {
    const { user } = await Auth.signUp({
      username: email,
      password: password,
      attributes: {
        name: name,
        email: email,
        preferred_username: username
      },
      autoSignIn: {
        // optional - enables auto sign in after user is confirmed
        enabled: true
      }
    });
    console.log(user);
    window.location.href = `/confirm?email=${email}`;
  } catch (error) {
    console.log(error);
    setErrors(error.message);
  }
  return false;
};
```

The code uses Cognito's `Auth.signUp` to create a new user, and redirect the browser to a confirmation page, where users enter the confirmation code that they received through their email.
The implementation of the Confirmation Page is already explain the section above.

Here is a new user in the AWS Console, that has been created through the front-end.

![New User through Signup](/assets/singup-new-user.png)

## Implement a Custom Recovery Page

The password recovery page has two main functions, request
to change a password, and then allow user to change that password
if they provide the correct confirmation code.

Therefore I needed to make two API calls, one to request a password change, and the second to make the change with the correct confirmation code and the new password.

I needed to edit the file `src/pages/RecoverPage.js` and overwrite the two onsubmit functions, as displayed below:

```js
onst onsubmit_send_code = async (event) => {
    event.preventDefault();
    setErrors('')
    Auth.forgotPassword(username)
      .then((data) => setFormState('confirm_code'))
      .catch((err) => setErrors(err.message));
    return false
  }

  const onsubmit_confirm_code = async (event) => {
    event.preventDefault();
    setErrors('')
    if (password == passwordAgain) {
      Auth.forgotPasswordSubmit(username, code, password)
        .then((data) => setFormState('success'))
        .catch((err) => setErrors(err.message));
    } else {
      setErrors('Passwords do not match')
    }
    return false
  }
```

These use two Cognito functions `Auth.forgotPassword` and `Auth.forgotPasswordSubmit`.

Here is an email from Cognito after a request to recover the password:

![Password reset](/assets/password-reset-code.png)

Here is the new password being set with the reset code:

![password-recover.png](/assets/password-recover.png)

Finally, here is a successful password reset screen:

![Successful password reset](/assets/password-reset.png)

## Verify JWT token server side

Currently, we are not doing any Cognito authorization on our backend, and this needs to be fixed...

In our `SigninPage.js` page, whenever a user successfully signs in we write an `access_token` to localStorage.

```js
localStorage.setItem(
  "access_token",
  user.signInUserSession.accessToken.jwtToken
);
```

We will need to pass this token with every API call that we make to our _flask-backend_.

For example: here is how we pass this token in HomePageFeed.js :

```js
const loadData = async () => {
    ...
      const res = await fetch(backend_url, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        },
        method: "GET"
      });
      let resJson = await res.json();
    ...
```

We basically add an `Authorization: Bearer access_token` header to every fetch call to our backend. This change is made in several files that need to load data from the flask-backend, such as in _ProfileInfo.js_

Now that changed the front-end we need to make changes in the backend-flask.

In the `app.py` add "Authorization" to the allowed cors list, in order to avoid CORS errors.

```py
cors = CORS(
  app,
  resources={r"/api/*": {"origins": origins}},
  expose_headers="location,link",
  allow_headers=["content-type","if-modified-since", "traceparent", "Authorization"],
  methods="OPTIONS,GET,HEAD,POST"
)
```

For this homework we will only secure the API route `/api/activities/home`.
We will make changes in the `data_home()` method of `App.py` and in the `HomeActivites.run()` method in the `/backend-flask/services/home_activities.py`

The data*home() method will use a \_nodejs sidecar* approach of validating Authorization JWT's and will be described in a different section below [here](#hard-decouple-the-jwt-verify-by-implementing-a-container-sidecar-pattern-using-awss-official-aws-jwt-verifyjs-library).

The HomeActivities.run() is modified to accept a cognito_user_id with a default of None. If a user id is provided the method will return results with a secret message, only visible to the logged in user. However if no user is provided then the secret message will not be sent.

In `/backend-flask/services/homeactivities.py`:

```py
class HomeActivities:
  def run(cognito_user_id=None):

    ##...

    if cognito_user_id != None:
      results.append({
        'uuid': '248959df-3079-4947-b847-9e0892d1bab4',
        'handle':  'SecretAgent',
        'message': 'This is a secret page. ONLY VISIBLE WHEN LOGGED IN.',
        'created_at': (now - timedelta(hours=1)).isoformat(),
        'expires_at': (now + timedelta(hours=12)).isoformat(),
        'likes': 0,
        'replies': []
      })

    ##...
    return results
```

Here is the home screen when the user is not authorized:

![]()

and here it is when it is authorized:

![Authorized Secret Message](/assets/authorized-secret-message.png)

# Additional Homework Challenges

## [Hard] Decouple the JWT verify by implementing a Container Sidecar pattern using AWS’s official Aws-jwt-verify.js library
