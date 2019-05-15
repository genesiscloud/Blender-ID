FROM blenderinstitute/blender-id-base:latest

COPY --chown=uwsgi:uwsgi staging/blender-id /var/www/blender-id/

WORKDIR /var/www/blender-id
COPY deploytime-settings-blenderid.py /var/www/blender-id/blenderid/settings.py
RUN poetry run ./manage.py collectstatic --noinput
WORKDIR /

# Do some quick copies to prevent small changes from requiring a rebuild of the base image.
COPY nginx/default.conf /etc/nginx/conf.d/
COPY root_files/* /

CMD ["/bin/sh", "/entrypoint.sh"]
