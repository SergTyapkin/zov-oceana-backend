# add user to docker group
getent group docker || sudo groupadd docker && # Add group if not exists
sudo usermod -aG docker "${USER}" &&
newgrp docker &&
sudo systemctl restart docker &&
echo "✅ Current user adds into group Docker" ||
echo "❌ Errors when adding user into group Docker"
