# Frontend Dockerfile for Render.com
# ── Stage 1: Build ──
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# Build arg for Google Client ID (injected at build time)
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

# ── Stage 2: Serve ──
FROM nginx:alpine

RUN apk add --no-cache gettext

COPY --from=build /app/dist /usr/share/nginx/html

# Nginx config template (envsubst replaces $PORT and $BACKEND_URL at runtime)
COPY deploy/nginx-render.conf /etc/nginx/templates/default.conf.template

# Entrypoint script
COPY deploy/frontend-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 10000

CMD ["/docker-entrypoint.sh"]
