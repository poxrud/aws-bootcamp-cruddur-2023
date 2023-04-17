FROM node:16-slim

ENV PORT=3050

RUN apt-get update && apt-get install -y curl

WORKDIR /app
COPY package*.json ./

RUN npm install

COPY . .

EXPOSE ${PORT}

CMD [ "node", "verify_cognito_token.js" ]