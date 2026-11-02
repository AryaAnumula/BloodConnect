FROM node:24-alpine
WORKDIR /app
COPY --chown=node:node . .
RUN mkdir -p /app/receipts && chown node:node /app/receipts
USER node
EXPOSE 3000
CMD ["node", "src/server.mjs"]
