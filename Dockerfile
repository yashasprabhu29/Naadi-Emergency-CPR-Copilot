# Naadi: one container that serves the built React site and the FastAPI backend
# from the same origin, so the browser needs no CORS and live audio uses wss://.

# ---- 1. Build the frontend ----
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Empty base URL: the built site calls the API on its own origin.
ENV VITE_API_BASE_URL=""
RUN npm run build

# ---- 2. Run the backend ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NAADI_STATIC_DIR=/app/frontend/dist \
    NAADI_DB_PATH=/app/data/naadi.sqlite3 \
    ENVIRONMENT=production
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
COPY --from=web /web/dist frontend/dist

RUN useradd --create-home --uid 10001 naadi && mkdir -p /app/data && chown -R naadi:naadi /app/data
USER naadi

# Render sets PORT. --proxy-headers makes rate limits see the real client IP.
EXPOSE 10000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
