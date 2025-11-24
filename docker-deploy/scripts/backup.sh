cd ./docker-deploy && \
# Create backup \
docker compose --env-file ../.env exec db bash -c "pg_dump -F c -b -U $(. "../.env"; echo "$POSTGRES_USER") $(. "../.env"; echo "$POSTGRES_DB") > /pg_backups/backup_$(date "+%A").sql.backup" && \
# Send backup on mail \
docker compose --env-file ../.env exec app python -m src.mainSendDatabaseBackupOnMail && \
echo "✅ Backups made and send to mail successfully" ||
echo "❌ Errors when making backups"
