#!/bin/sh

set -e
echo -n "Starting up at "
date -Iseconds

# echo "Ensuring log directories are set up correctly"
mkdir -p /var/log/uwsgi /var/log/nginx /var/log/blender-id

touch /var/log/uwsgi/blender-id.log
touch /var/log/blender-id/blender-id.log

chown -R uwsgi:uwsgi /var/log/uwsgi   /var/log/blender-id
chmod 2775           /var/log/uwsgi   /var/log/blender-id
chmod  664           /var/log/uwsgi/* /var/log/blender-id/*

mkdir -p /var/www/blender-id/media
chown uwsgi:uwsgi /var/www/blender-id/media
chmod 2775 /var/www/blender-id/media

# Start nginx first, so that it can at least serve a "we'll be right back" page.
echo "Starting nginx"
nginx

function shutdown {
    echo "Shutting down"
    set +e

    [ -e /var/run/uwsgi-blender-id.pid ] && uwsgi --stop /etc/uwsgi/apps-enabled/blender-id.ini
    nginx -s stop

    echo "Shutdown function is done"
}
trap shutdown EXIT

echo "Running migrations"
cd /var/www/blender-id
poetry run python3 manage.py migrate

echo "Starting uWSGI"
uwsgi /etc/uwsgi/uwsgi.ini

echo "Waiting for stuff"
set +e
tail -f /dev/null &
KILLPID=$!

function finish {
    echo "Finishing Docker image"
    set -x
    kill $KILLPID
}
trap finish QUIT
trap finish TERM
trap finish INT

wait

echo "Done waiting, shutting down some stuff cleanly"
