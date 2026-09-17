#!/usr/bin/env bash
# =============================================================================
# KRIO — Deploy Database Script
# Jalankan skrip migrasi 0001_init.sql ke PostgreSQL
#
# Usage:
#   ./scripts/deploy_db.sh                           # pakai DATABASE_URL
#   ./scripts/deploy_db.sh postgresql://user@host/db  # URL spesifik
#   DATABASE_URL=... ./scripts/deploy_db.sh           # via env var
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_FILE="${SCRIPT_DIR}/../db/migrations/0001_init.sql"
TEST_FILE="${SCRIPT_DIR}/../db/tests/0001_init_test.sql"

DATABASE_URL="${1:-${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/krio_dev}}"

# Ekstrak host:port dari URL untuk psql
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|://\([^:]*\):.*|\1|p')

echo "============================================="
echo "KRIO — Deploy Database"
echo "============================================="
echo "Host    : ${DB_HOST:-localhost}"
echo "Port    : ${DB_PORT:-5432}"
echo "Database: ${DB_NAME:-krio_dev}"
echo "User    : ${DB_USER:-postgres}"
echo "============================================="
echo ""

# Cek psql tersedia
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql tidak ditemukan. Install postgresql-client terlebih dahulu."
    exit 1
fi

# Cek file migrasi ada
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "ERROR: File migrasi tidak ditemukan: $MIGRATION_FILE"
    exit 1
fi

echo "[1/3] Menjalankan migrasi 0001_init.sql..."
PGPASSWORD="${DATABASE_URL##*:}" psql -X -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$MIGRATION_FILE" \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}"

echo ""
echo "[2/3] Menjalankan uji integritas..."
PGPASSWORD="${DATABASE_URL##*:}" psql -X -d "$DB_NAME" -f "$TEST_FILE" \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}"

echo ""
echo "[3/3] Verifikasi tabel..."
PGPASSWORD="${DATABASE_URL##*:}" psql -X -d "$DB_NAME" -c "\dt" \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}"

echo ""
echo "============================================="
echo "DEPLOY SELESAI"
echo "============================================="
