#!/bin/bash -e

REMOTE_DOCKER_COMPOSE_DIR="/var/www/sintel-blender-org-management"

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi
MY_DIR="$(dirname "$($readlink -f "$0")")"
source "$MY_DIR/settings.sh"

#################################################################################
if [ -z "$1" ]; then
    echo "Use $0 sintel.blender.org" >&2
    exit 1
fi
DEPLOYHOST="$1"
SSH_OPTS="-o ClearAllForwardings=yes -o PermitLocalCommand=no"
SSH="ssh $SSH_OPTS $DEPLOYHOST"
SCP="scp $SSH_OPTS"

echo -n "Deploying to $DEPLOYHOST… "

if ! ping $DEPLOYHOST -q -c 1 -W 2 >/dev/null; then
    echo "host $DEPLOYHOST cannot be pinged, refusing to deploy." >&2
    exit 2
fi

cat <<EOT
[ping OK]

Make sure that you have pushed the $DOCKER_TAG
docker image to Docker Hub.

press [ENTER] to continue, Ctrl+C to abort.
EOT
read dummy

#################################################################################
echo "==================================================================="
echo "Bringing remote Docker up to date…"
$SSH -T <<EOT
set -e
cd $REMOTE_DOCKER_COMPOSE_DIR
docker pull $DOCKER_TAG
docker-compose up -d
EOT

echo
echo "==================================================================="
echo "Deploy to $DEPLOYHOST done."
echo "==================================================================="
