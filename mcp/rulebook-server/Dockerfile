# Build context is the repository root (see az acr build --file/. in
# .github/workflows/deploy-and-evaluate.yml) so data/synthetic/ ships
# alongside the server, matching rulebook_data_loader.py's
# REPO_ROOT = Path(__file__).resolve().parents[2] resolution.
FROM python:3.13-slim

WORKDIR /app

COPY mcp/rulebook-server/requirements.txt mcp/rulebook-server/requirements.txt
RUN pip install --no-cache-dir -r mcp/rulebook-server/requirements.txt

COPY mcp/rulebook-server mcp/rulebook-server
COPY data data

WORKDIR /app/mcp/rulebook-server

EXPOSE 8002

CMD ["python", "main.py"]
