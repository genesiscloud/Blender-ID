# Deployment

How to deploy Blender ID in production and how to push updates.


## Standard deploy playbook

* Merge the required commits from `master` into `production` branch
* Push `production` to origin
* Run unittests
* Run `__deploy.sh___`


## Documentation deploy playbook

* Move to `docs`, run `mkdocs serve` and check that the docs look good at the address provided by `mkdocs`.
* `export RSYNC_PASSWORD=secret`
* `rsync -azP site/ rsync://blenderid@www.blender.org/id/`


## Full setup from scratch

Assuming deployment on FreeBSD with uWSGI, take care to:

- Install `python36`, `devel/py-pipenv`, `apache24`, `a24_mod_proxy_uwsgi`, `mysql56-server`, and
  `sysutils/daemontools`.
- Add the following to `/etc/make.conf`. Remove the `.if` and `.endif` lines if you're fine having
  Python 3.6 as a global default.

      .if ${.CURDIR:M*/www/uwsgi*}
      DEFAULT_VERSIONS=python=3.6 python3=3.6
      .endif

- Build and install the `www/uwsgi` port and run `make clean`.
- Add the `uwsgi` user to the `www` group, or graceful restarts won't work due to permission
  problems. uWSGI tries to change ownership of `/tmp/uwsgi.sock` to `uwsgi:www`, and not being in
  the `www` group this would fail.
- Create a Git clone of the `production` branch at `/data/www/vhosts/www.blender.org/blender-id/`
- Create the VirtualEnv:

      cd /data/www/vhosts/www.blender.org/blender-id
      export PIPENV_VENV_IN_PROJECT=1
      pipenv install --deploy

- Use the following file in `/usr/local/etc/uwsgi/uwsgi.ini`:

      [uwsgi]
      master = true
      enable-threads = true
      processes = 2
      virtualenv = /data/www/vhosts/www.blender.org/blender-id/.venv/
      chdir = /data/www/vhosts/www.blender.org/blender-id/
      wsgi-file = /data/www/vhosts/www.blender.org/blender-id/blenderid/wsgi.py
      buffer-size = 32768

- Enable the following Apache modules:

      LoadModule proxy_module libexec/apache24/mod_proxy.so
      LoadModule proxy_uwsgi_module libexec/apache24/mod_proxy_uwsgi.so

- Use the following configuration for Apache, I placed it in `Includes/uwsgi.conf`:

      Alias /id/static/ /data/www/vhosts/www.blender.org/blender-id/static/
      <Directory /data/www/vhosts/www.blender.org/blender-id/static/>
          Require all granted
      </Directory>

      ProxyPass /id/static/ "!"
      ProxyPass /id unix:/tmp/uwsgi.sock|uwsgi://blender-id/
      ProxyPassReverse /id "www.blender.org/id/"

- Enable the required services in `/etc/rc.conf`:

      mysql_enable="YES"
      uwsgi_enable="YES"
      apache24_enable="YES"

      # Appears to not honour the configfile flag, pass as --ini instead
      # -- troubled/sybren @ Nov 21 2017 hangout chat
      #uwsgi_configfile="/usr/local/etc/uwsgi/uwsgi.ini"
      uwsgi_flags="-L --ini /usr/local/etc/uwsgi/uwsgi.conf"

      svscan_enable="YES"
      svscan_logdir="/var/log/service"
      svscan_logmax=104857600

- Create the directories `/var/log/service` and `/var/service/blender-id-flush-webhooks`,
  put this file into `/var/service/blender-id-flush-webhooks/run` and `chmod +x` it:

      #!/bin/sh

      BASE=/data/www/vhosts/www.blender.org
      exec su borg -c bash -ex <<EOT
      cd $BASE/blender-id
      exec ./.venv/bin/python3 manage.py flush_webhooks -m -v 0
      EOT

- Start the daemon supervisor with `sudo service svscan start` if necessary.

- Set up the following cron job:

      47  *  *   *   *  cd /data/www/vhosts/www.blender.org/blender-id && ./.venv/bin/python3 manage.py cleartokens
      57  *  *   *   *  cd /data/www/vhosts/www.blender.org/blender-id && ./.venv/bin/python3 manage.py thumbnail cleanup
