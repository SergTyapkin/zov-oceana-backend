echo "Now read README.md and setup another deploy environments variables." &&
echo "It seems like values must be:" &&
echo "" &&
echo "SSH_DEPLOY_KEY=<private-key-that-you've-seen-before>  [! MUST BE SECRET VARIABLE !]" &&
echo "SERVER_USERNAME=$(whoami)  [! MUST BE SECRET VARIABLE !]" &&
echo "DEPLOY_HOST=$(. "./.env"; echo "$VITE_DEPLOY_HOSTNAME")" &&
echo "PROJECT_PATH=$(pwd)" &&
echo "" &&
echo "[press Enter to finish setup...]" &&
read ENTER
