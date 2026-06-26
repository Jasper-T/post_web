ARG DOCKER_HUB_MIRROR=docker.io/library

FROM ${DOCKER_HUB_MIRROR}/node:20-alpine AS builder

WORKDIR /app

ENV npm_config_loglevel=warn

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM ${DOCKER_HUB_MIRROR}/nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
