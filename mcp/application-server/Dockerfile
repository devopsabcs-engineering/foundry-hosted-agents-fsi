# Build context is the repository root (see az acr build --file/. in
# .github/workflows/deploy-and-evaluate.yml) so data/synthetic/ ships
# alongside the server, matching application_data_loader.py's
# REPO_ROOT = Path(__file__).resolve().parents[2] resolution.
FROM python:3.13-slim

WORKDIR /app

COPY mcp/application-server/requirements.txt mcp/application-server/requirements.txt
RUN pip install --no-cache-dir -r mcp/application-server/requirements.txt

COPY mcp/application-server mcp/application-server
COPY data data

WORKDIR /app/mcp/application-server

EXPOSE 8001

CMD ["python", "main.py"]
