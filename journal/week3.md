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

To create a custom signin page I needed to modify the file `/frontend-react-js/src/pages/SigninPage.js`.
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
