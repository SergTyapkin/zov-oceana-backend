cd docker-deploy &&
docker compose --env-file ../.env down &&
echo "✅ Docker containers stopped" ||
echo "❌ Errors when stopping docker containers"
