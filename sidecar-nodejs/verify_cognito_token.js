"use strict";

import express from "express";
import { CognitoJwtVerifier } from "aws-jwt-verify";

// Constants
const PORT = process.env.EXPOSEDPORT || 3050;
const HOST = "0.0.0.0";

const verifier = CognitoJwtVerifier.create({
  userPoolId: process.env.COGNITO_USER_POOL_ID,
  tokenUse: "access",
  clientId: process.env.COGNITO_WEB_CLIENT_ID,
});

// App
const app = express();
app.get("/verify-cognito-token", async (req, res) => {
  try {
    const token = req.headers.authorization.split(" ")[1];
    const payload = await verifier.verify(token);
    res.status(200).send(payload);
  } catch (err) {
    console.error("Verification ERROR: ", err);
    res.status(401).send(err.message);
  }
});

app.get("/health-check", async (req, res) => {
  res.send("OK");
});

// Catch-all middleware for unmatched routes
app.use((req, res) => {
  res.status(404).send("404: Page not found");
});

app.listen(PORT, HOST, () => {
  console.log(`Running on http://${HOST}:${PORT}`);
});
