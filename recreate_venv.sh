#!/usr/bin/env bash

#########################################
# (Re)create the Blender ID virtualenv  #
#########################################
# This is used on our production server #
# to easily recreate the venv after     #
# upgrading Python or the system.       #
#########################################

set -e

MY_DIR=$(dirname $(readlink -f $0))
cd $MY_DIR

VENV=./.venv

if [ -e $VENV-DESTROYED ]; then
    echo "$VENV-DESTROYED exists; remove that one first."
    exit 1
fi

if [ -e $VENV ]; then
    echo "Press [ENTER] to DESTROY the current virtualenv \"$VENV\" and recreate it."
else
    echo "Press [ENTER] to create a new virtualenv at $VENV"
fi
read dummy

[ -e $VENV ] && mv $VENV $VENV-DESTROYED

python3.6 -m venv $VENV
poetry install --no-dev  # no need to activate, Poetry automatically picks up .venv

echo
echo "Done"
[ -e $VENV-DESTROYED ] && echo "Please remove $VENV-DESTROYED if everything is OK."
