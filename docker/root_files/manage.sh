#!/bin/bash
cd /var/www/blender-id
exec poetry run ./manage.py "$@"
