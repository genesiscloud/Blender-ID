#!/bin/bash -e

PROJECT_NAME="blender-id"

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi

MY_DIR="$(dirname "$($readlink -f "$0")")"
source "$MY_DIR/settings.sh"
cd "$MY_DIR"


case "$1" in
    all|full)
        docker build --file Dockerfile.base . -t ${DOCKER_TAG}-base
        ;;
    quick)
        ;;
    *)
        echo "Usage: $0 quick|full" >&2
        exit 3
        ;;
esac

docker build . -t $DOCKER_TAG

echo
echo "==================================================================="
echo "Docker image of ${PROJECT_NAME} is complete."
echo "==================================================================="
echo -n "Press [ENTER] to push to Docker Hub..."
read dummy
docker push $DOCKER_TAG

echo
echo "Done"
