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
docker compose up -d postgres
python scripts/run_local_demo.py
```

The HTTP API is exposed at `/api/v1/orchestrate`, the health check is `/healthz`, and the MCP server is mounted at `/mcp`.

For the local developer path used in this repository:

- Start the bundled Postgres + pgvector service with `docker compose up -d postgres`.
- Use a local `.env` that leaves `ALLOYDB_INSTANCE_URI` empty and points `ALLOYDB_DSN` to `127.0.0.1`.
- The container auto-applies [`db/schema.sql`](/Users/kade/Codes/adk-gai-hackathon/db/schema.sql) and demo seed data from [`db/local_seed.sql`](/Users/kade/Codes/adk-gai-hackathon/db/local_seed.sql) on first boot.
- Start the API with [`scripts/run_local_demo.py`](/Users/kade/Codes/adk-gai-hackathon/scripts/run_local_demo.py).
- If you need a public demo URL, run `ngrok http 8080` after the FastAPI server is up.

## Initialize the Database

Apply [`db/schema.sql`](/Users/kade/Codes/adk-gai-hackathon/db/schema.sql) to your AlloyDB database after enabling the `vector` extension.

## Deploy to Cloud Run

```bash
gcloud builds submit --config cloudbuild.yaml
```

For Cloud Run, the scaffold supports two database connection modes:

- Recommended production path: set `ALLOYDB_INSTANCE_URI` and use the AlloyDB Python connector over private IP.
- Local fallback: omit `ALLOYDB_INSTANCE_URI` and use `ALLOYDB_DSN`.
