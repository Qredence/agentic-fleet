# ============================================================================
# AgenticFleet Frontend Dockerfile
# Lightweight nginx-based production image
# ============================================================================

FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# Production - nginx alpine (~25MB)
# -----------------------------------------------------------------------------
FROM nginx:alpine

# Custom nginx config for SPA + API proxy
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
