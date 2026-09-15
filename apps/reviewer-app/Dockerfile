# Build context is the repository root, not this directory, so the case store
# modules can be copied from src/quote-preparation-agent instead of adding a
# third vendored copy of approval_repository.py to the repository:
#   docker build -f apps/reviewer-app/Dockerfile .
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY apps/reviewer-app/frontend/package.json apps/reviewer-app/frontend/package-lock.json ./
RUN npm ci
COPY apps/reviewer-app/frontend/index.html apps/reviewer-app/frontend/vite.config.js ./
COPY apps/reviewer-app/frontend/src ./src
COPY apps/reviewer-app/frontend/tests ./tests
RUN npm test && npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY apps/reviewer-app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY apps/reviewer-app/app.py apps/reviewer-app/auth.py ./
COPY src/quote-preparation-agent/approval_repository.py src/quote-preparation-agent/case_store.py \
     src/quote-preparation-agent/sqlite_case_store.py src/quote-preparation-agent/cosmos_case_store.py ./
COPY --from=frontend /build/dist ./frontend/dist
RUN python -c "from app import Settings, create_app; create_app(Settings('tenant', 'client'))"
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
