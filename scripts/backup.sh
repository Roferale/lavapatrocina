#!/bin/bash
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/lava_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Fazendo backup do banco de dados..."
docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-lava}" \
    -d "${POSTGRES_DB:-lavadb}" \
    > "$BACKUP_FILE"

echo "Backup salvo em: $BACKUP_FILE"

# Keep only last 10 backups
ls -t "${BACKUP_DIR}"/*.sql | tail -n +11 | xargs -r rm
echo "Backups antigos removidos. Mantidos os 10 mais recentes."
