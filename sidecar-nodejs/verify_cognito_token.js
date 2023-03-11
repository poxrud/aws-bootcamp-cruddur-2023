'use strict';

import express from 'express';
import { CognitoJwtVerifier } from "aws-jwt-verify";

// Constants
const PORT = process.env.EXPOSEDPORT || 3050;
const HOST = '0.0.0.0';

const verifier = CognitoJwtVerifier.create({
  userPoolId: process.env.COGNITO_USER_POOL_ID,
  tokenUse: "access",
  clientId: process.env.COGNITO_WEB_CLIENT_ID,
});


// App
const app = express();
app.get('/verify-cognito-token', async (req, res) => {
  try {
    const token = req.headers.authorization.split(' ')[1];
    const payload = await verifier.verify(token);
    res.sendStatus(200);
  } catch (err) {
    console.error("Verification ERROR: ", err);
    res.status(401).send(err.message);
  }
});

app.listen(PORT, HOST, () => {
  console.log(`Running on http://${HOST}:${PORT}`);
});



