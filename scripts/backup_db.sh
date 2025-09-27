#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DATABASE_URL="postgresql://user:pass@host:port/db" ./scripts/backup_db.sh
# Requires: pg_dump in PATH

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "❌ DATABASE_URL is not set. Export it and re-run."
  echo "   export DATABASE_URL=\"postgresql://user:pass@host:port/db\""
  exit 1
fi

# Ensure backups dir
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/supabase_backup_$TS.sql.gz"

echo "🗄  Backing up database to $OUT_FILE"
pg_dump "$DATABASE_URL" \
  --format=plain \
  --no-owner --no-privileges \
  --clean \
  | gzip -9 > "$OUT_FILE"

ls -lh "$OUT_FILE"
echo "✅ Backup complete." 