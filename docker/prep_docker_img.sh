#!/bin/bash -e

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

ROOT="$(dirname "$MY_DIR")"
STAGING_DIR="$ROOT/docker/staging"
PROJECT_NAME="blender-id"

# Check that production branch has been pushed.
if [ -n "$(git log origin/$DEPLOY_BRANCH..$DEPLOY_BRANCH --oneline)" ]; then
    echo "WARNING: not all changes to the $DEPLOY_BRANCH branch have been pushed."
    echo "Press [ENTER] to continue deploying current origin/$DEPLOY_BRANCH, CTRL+C to abort."
    read dummy
fi

rm -rf "$STAGING_DIR/$PROJECT_NAME"
mkdir -p $STAGING_DIR

function git_clone() {
    PYTHON_NAME="$1"
    URL="$2"
    BRANCH="$DEPLOY_BRANCH"

    set -e
    echo "==================================================================="
    echo "CLONING REPO ON $PROJECT_NAME @$BRANCH"
    git -C "$STAGING_DIR" clone --depth 1 --branch $BRANCH $URL $PROJECT_NAME
    git -C "$STAGING_DIR/$PROJECT_NAME" submodule init
    git -C "$STAGING_DIR/$PROJECT_NAME" submodule update --recommend-shallow

    # We need *some* settings to be able to run `manage.py collectstatic` later.
    # That command is given while building the docker image.
    cp "$MY_DIR/deploytime-settings-$PYTHON_NAME.py" $STAGING_DIR/$PROJECT_NAME/$PYTHON_NAME/settings.py
}

git_clone blenderid "$GIT_URL"

# Gulp everywhere
pushd "$STAGING_DIR/$PROJECT_NAME"
./gulp
rm -rf node_modules
mkdir -p media
popd

echo
echo "==================================================================="
echo "Deploy of ${PROJECT_NAME} is ready for dockerisation."
echo "==================================================================="
