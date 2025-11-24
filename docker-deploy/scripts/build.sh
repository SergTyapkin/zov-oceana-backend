cd ./docker-deploy &&
docker compose --env-file ../.env --progress=plain build &&
echo "✅ Docker image built" ||
echo "❌ Errors when building docker image"

