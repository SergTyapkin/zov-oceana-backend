cp --no-clobber .env.example .env &&
echo "" &&
echo "Edit .env file." &&
echo "Set right APP_CONTAINER_NAME - it's name of backend app in docker network" &&
echo "Set right POSTGRES_PASSWORD - it's any your strong password for your db" &&
echo "Set right PORT - it's port of backend" &&
echo "[press Enter...]" &&
read ENTER &&
nano .env

echo "" &&
echo "Is your frontend deployed on this computer or docker-cluster in docker container? (y/N): " &&
read USER_ANSWER &&
cat ./docker-deploy/docker-compose.template.yaml > ./docker-deploy/docker-compose.yaml &&
if [[ $USER_ANSWER == "Y" ]] || [[ $USER_ANSWER == "y" ]] || [[ $USER_ANSWER == "yes" ]] || [[ $USER_ANSWER == "Yes" ]] || [[ $USER_ANSWER == "YES" ]]
then
  echo "Enter the backend-frontend docker network name (you can edit it after this setting at bottom of docker-compose.yml): " &&
  read USER_ANSWER &&
  echo "    name: $USER_ANSWER
" >> ./docker-deploy/docker-compose.yaml
fi
