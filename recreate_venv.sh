#!/bin/bash

#########################################
# (Re)create the Blender ID virtualenv  #
#########################################
# This is used on our production server #
# to easily recreate the venv after     #
# upgrading Python or the system.       #
#########################################


VENV=${1:-./venv}

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
virtualenv -p $(which python3.6) $VENV
. $VENV/bin/activate
pip install -U pip
pip install -U -r requirements.txt
deactivate

echo
echo "Done"
[ -e $VENV-DESTROYED ] && echo "Please remove $VENV-DESTROYED if everything is OK."
