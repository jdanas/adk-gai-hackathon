# FlowMind

FlowMind is a prototype multi-agent backend API that accepts unstructured prompts and routes them across task, calendar, and notes agents. The service is designed for Google Cloud Run, uses FastAPI for the HTTP layer, Google ADK for agent definitions, MCP-compatible tool wrappers for system actions, and AlloyDB AI for relational and vector-backed storage.

## Project Structure

```text
.
├── agents/
│   ├── __init__.py
│   └── flowmind_agents.py
├── db/
│   ├── __init__.py
│   ├── connection.py
│   └── schema.sql
├── tools/
│   ├── __init__.py
│   └── mcp_tools.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── cloudbuild.yaml
├── config.py
├── main.py
└── requirements.txt
```

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

The HTTP API is exposed at `/api/v1/orchestrate`, the health check is `/healthz`, and the MCP server is mounted at `/mcp`.

## Initialize the Database

Apply [`db/schema.sql`](/Users/kade/Codes/adk-gai-hackathon/db/schema.sql) to your AlloyDB database after enabling the `vector` extension.

## Deploy to Cloud Run

```bash
gcloud builds submit --config cloudbuild.yaml
```

For Cloud Run, the scaffold supports two database connection modes:

- Recommended production path: set `ALLOYDB_INSTANCE_URI` and use the AlloyDB Python connector over private IP.
- Local fallback: omit `ALLOYDB_INSTANCE_URI` and use `ALLOYDB_DSN`.
