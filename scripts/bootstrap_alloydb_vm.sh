#!/bin/bash
set -euo pipefail

exec > >(tee /var/log/flowmind-bootstrap.log) 2>&1

METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
HEADER="Metadata-Flavor: Google"

get_attr() {
  curl -fsS -H "$HEADER" "${METADATA_URL}/$1"
}

echo "Starting FlowMind AlloyDB bootstrap on VM..."

REPO_RAW_BASE="$(get_attr repo-raw-base)"
ALLOYDB_INSTANCE_URI="$(get_attr alloydb-instance-uri)"
ALLOYDB_DATABASE="$(get_attr alloydb-database)"
ALLOYDB_USER="$(get_attr alloydb-user)"
ALLOYDB_PASSWORD="$(get_attr alloydb-password)"
ALLOYDB_IP_TYPE="$(get_attr alloydb-ip-type)"

apt-get update
apt-get install -y python3-venv curl ca-certificates

mkdir -p /opt/flowmind/scripts /opt/flowmind/db

curl -fsSL "${REPO_RAW_BASE}/scripts/init_alloydb.py" -o /opt/flowmind/scripts/init_alloydb.py
curl -fsSL "${REPO_RAW_BASE}/db/schema.sql" -o /opt/flowmind/db/schema.sql

cat > /opt/flowmind/.env <<EOF
ALLOYDB_INSTANCE_URI=${ALLOYDB_INSTANCE_URI}
ALLOYDB_DATABASE=${ALLOYDB_DATABASE}
ALLOYDB_USER=${ALLOYDB_USER}
ALLOYDB_PASSWORD=${ALLOYDB_PASSWORD}
ALLOYDB_IP_TYPE=${ALLOYDB_IP_TYPE}
EOF

python3 -m venv /opt/flowmind/.venv
/opt/flowmind/.venv/bin/pip install --upgrade pip
/opt/flowmind/.venv/bin/pip install 'google-cloud-alloydb-connector[pg8000]==1.9.1' pg8000==1.31.5

cd /opt/flowmind
/opt/flowmind/.venv/bin/python /opt/flowmind/scripts/init_alloydb.py

touch /opt/flowmind/bootstrap.done
echo "FlowMind AlloyDB bootstrap complete."
