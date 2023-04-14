import { Auth } from "aws-amplify";

// check if we are authenicated
const checkAuth = async (setUser) => {
  Auth.currentAuthenticatedUser({
    bypassCache: false,
  })
    .then((cognito_user) => {
      setUser({
        display_name: cognito_user.attributes.name,
        handle: cognito_user.attributes.preferred_username,
      });
    })
    .catch((err) => {
      console.log(err);
    });
};

const getAccessToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getAccessToken().getJwtToken();
  } catch (err) {
    console.log(err);
  }
};

export { checkAuth, getAccessToken };
