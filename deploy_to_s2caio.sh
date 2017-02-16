IP=10.30.233.251
SSH_USER=crystal
SSH_PASSWORD=crystal

DEST_DIRECTORY=/home/crystal/Development

#sshpass -p $SSH_PASSWORD rsync --progress --delete -arz --exclude '.git' -e ssh ../SDS-dashboard/ $SSH_USER@$IP:$DEST_DIRECTORY/SDS-Dashboard
sshpass -p $SSH_PASSWORD rsync --progress --delete -arz --exclude '.git' -e ssh ../Crystal-Controller-nou/ $SSH_USER@$IP:$DEST_DIRECTORY/controller