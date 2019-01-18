# Development setup

After cloning the Git repo, perform these steps to create a working dev server:

- Copy `blenderid/__settings.py` to `blenderid/settings.py` and adjust for your needs.
- Run `git submodule init` and `git submodule update`
- Create a virtual environment (with Python 3.6) by running `pipenv install --dev`
  (if you get an error when installing the `mysqlclient` package on macOS,
  [change your mysql_config](https://github.com/PyMySQL/mysqlclient-python#note-about-bug-of-mysql-connectorc-on-macos)).
  Note that from now on we assume you run from a `pipenv shell` or prefix commands with
  `pipenv run`.
- Create the database with `mysqladmin create blender_id --default-character-set=utf8`.
- Run `./manage.py migrate` to migrate your database to the latest version.
- Run `./manage.py createcachetable` to create the cache table in the database.
- Run `mkdir media` to create the directory that'll hold uploaded files
  (such as images for the badges).
- In production, set up a cron job that calls the
  [cleartokens](https://django-oauth-toolkit.readthedocs.io/en/latest/management_commands.html#cleartokens)
  management command regularly.
- In production, set up a cron job that calls the `flush_webhooks --flush -v 0` management command
  regularly.
- Run `./manage.py createsuperuser` to create super user
- Load any fixtures you want to use.
   - list fixtures  `ls */fixtures/*`
   - `./manage.py loaddata default_site`
   - `./manage.py loaddata default_roles`
   - `./manage.py loaddata blender_cloud_devserver`
   - `./manage.py loaddata blender_cloud_dev_webhook`
   - `./manage.py loaddata flatpages`
- Run `./manage.py collectmedia` to collect media from fixtures and place into the media directory.
- Run `./gulp`  to compile javascript
- Add to /etc/hosts  127.0.0.1 id.local
- Run `./manage.py runserver`


## Setting up the Blender Store (and other `bid_api` users)

To allow the Blender Store to call our API endpoints, do the following:

- Add an OAuth2 application for the API, name it "Blender ID API". You can choose any name, but
  it's nice if we all use the same so we can recognise it. Set it to 'Confidential' and 'Resource
  owner password-based'.
- Make sure that the `cloud_demo` and `cloud_subscriber` roles exist, and that they are badges.
  Add a role `cloud_badger` and allow it to manage the above roles.
- Add a user for the Blender Store, for example using "yourname+store@yourdomain.com" as email
  address. The password doesn't matter -- give it a long one and forget about it. Give the user the
  `cloud_badger` role.
- Add an OAuth2 token to the Blender Store user for the Blender ID API application. Make sure it
  doesn't expire any time soon (e.g. somewhere in the year 2999). Give it the scopes
  `badger`, `authenticate`, and `usercreate`.
- Configure the Blender Store to use this token to authenticate its API calls.


## Setting up the Documentation system

We use [mkdocs](https://www.mkdocs.org/) for documentation generation.

- Make sure your local pipenv is set up (see the first part of this page)
- Move to the `docs` directory
- Run `mkdocs serve` and browse to the location suggested by the command output

## TODO

1. Check out the [default management
   endpoints](https://django-oauth-toolkit.readthedocs.io/en/latest/tutorial/tutorial_02.html#make-your-api)
   of the Django OAuth Toolkit.


## Blender ID add-on support

The Blender ID add-on specific authentication module basically provides a slight less secure but
more convenient way to obtain an OAuth authentication token. Effectively it allows username/password
entry in the application itself, rather than spawning a web browser.


## Troubleshooting

### "Site matching query does not exist."

Do this:

    pipenv run ./manage.py loaddata default_site

Then access your site at http://id.local:8000/. Add an entry to your hosts file if necessary.
