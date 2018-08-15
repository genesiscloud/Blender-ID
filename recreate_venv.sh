#!/bin/bash -e

#########################################
# (Re)create the Blender ID virtualenv  #
#########################################
# This is used on our production server #
# to easily recreate the venv after     #
# upgrading Python or the system.       #
#########################################

MY_DIR=$(dirname $(readlink -f $0))
cd $MY_DIR

export PIPENV_VENV_IN_PROJECT=1
VENV=.venv

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

pipenv install --deploy

echo
echo "Done"
[ -e $VENV-DESTROYED ] && echo "Please remove $VENV-DESTROYED if everything is OK."
