"""
Deploy-time settings.

These settings are used during the preparation of the Docker image,
so that we can run `manage.py collectstatic`. The settings should
mimick the production settings, but of course not contain any secrets.

The actual settings should be mounted using a Docker volume.
"""

# noinspection PyUnresolvedReferences
from blenderid.common_settings import *

DEBUG = False
SECRET_KEY = r'''1234'''

# Set this to the IP address of the Docker host's docker0 interface in
# your blender_id_settings.py, if it's different than this address:
EMAIL_HOST = '172.17.0.1'


import sys
import os

if os.path.exists('/var/www/settings/blender_id_settings.py'):
    sys.path.append('/var/www/settings')
    from blender_id_settings import *
