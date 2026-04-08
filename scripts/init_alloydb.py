from __future__ import annotations

import os
from pathlib import Path

import pg8000
from google.cloud.alloydbconnector import Connector
from google.oauth2.credentials import Credentials


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "db" / "schema.sql"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False

    for char in sql:
        if char == "'":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue
        current.append(char)

    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def connect_db(connector: Connector, database: str):
    return connector.connect(
        env("ALLOYDB_INSTANCE_URI"),
        "pg8000",
        user=env("ALLOYDB_USER"),
        password=env("ALLOYDB_PASSWORD"),
        db=database,
        ip_type=env("ALLOYDB_IP_TYPE", "PRIVATE"),
    )


def ensure_database(connector: Connector, database_name: str) -> None:
    print("Connecting to postgres database for bootstrap...", flush=True)
    connection = connect_db(connector, "postgres")
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        print(f"Checking whether database '{database_name}' exists...", flush=True)
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,),
        )
        exists = cursor.fetchone()
        if not exists:
            print(f"Creating database '{database_name}'...", flush=True)
            cursor.execute(f'CREATE DATABASE "{database_name}"')
        else:
            print(f"Database '{database_name}' already exists.", flush=True)
    finally:
        cursor.close()
        connection.close()


def apply_schema(connector: Connector, database_name: str) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    print(f"Connecting to database '{database_name}' to apply schema...", flush=True)
    connection = connect_db(connector, database_name)
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        for statement in split_sql_statements(schema_sql):
            preview = statement.splitlines()[0][:80]
            print(f"Executing: {preview}", flush=True)
            cursor.execute(statement)
    finally:
        cursor.close()
        connection.close()


def main() -> None:
    load_env_file(ROOT / ".env")
    database_name = env("ALLOYDB_DATABASE")
    access_token = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN")
    connector_kwargs: dict[str, object] = {"refresh_strategy": "lazy"}
    if access_token:
        print("Using GOOGLE_OAUTH_ACCESS_TOKEN for connector authentication.", flush=True)
        connector_kwargs["credentials"] = Credentials(token=access_token)

    with Connector(**connector_kwargs) as connector:
        ensure_database(connector, database_name)
        apply_schema(connector, database_name)

    print(f"Initialized AlloyDB database '{database_name}' using {SCHEMA_PATH}.")


if __name__ == "__main__":
    main()
