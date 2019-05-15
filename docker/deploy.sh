#!/bin/sh -ex

# Everything to deploy in one script. Just takes some presses on the ENTER key.
MODE="${1:-quick}"

# If we can't connect to the Docker daemon continuing is futile.
if ! docker info > /dev/null 2>&1; then
    echo "Unable to connect to the Docker daemon, start it please." >&2
    exit 42
fi

./prep_docker_img.sh
./build_docker_img.sh "$MODE"
./2server.sh sintel.blender.org
