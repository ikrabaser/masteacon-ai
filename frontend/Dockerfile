# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Serve stage ---
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
# The official nginx image envsubst's every *.template file here into
# /etc/nginx/conf.d/ at container start (docker-entrypoint.d/20-envsubst-on-
# templates.sh), substituting ${VAR} using whatever's in the container's own
# environment — this is what keeps client_max_body_size in sync with
# MAX_UPLOAD_SIZE_MB (see nginx.conf.template and docker-compose.yml) without
# a custom entrypoint.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV MAX_UPLOAD_SIZE_MB=20

EXPOSE 80
