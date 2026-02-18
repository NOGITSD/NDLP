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

COPY --from=build /app/dist /usr/share/nginx/html

# Use Render-specific nginx config
COPY deploy/nginx-render.conf /etc/nginx/conf.d/default.conf

EXPOSE 8000

CMD ["nginx", "-g", "daemon off;"]
