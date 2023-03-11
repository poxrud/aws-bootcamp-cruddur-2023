FROM node:16-slim

ENV PORT=3050

WORKDIR /app
COPY package*.json ./

RUN npm install

COPY . .

EXPOSE ${PORT}

CMD [ "node", "verify_cognito_token.js" ]