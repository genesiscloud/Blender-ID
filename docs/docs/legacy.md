# Legacy

Historical notes on Blender ID and its previous implementations.

## Differences with previous Blender ID

Even though we have tried to keep the API the same, there are a few subtle differences between this
Blender ID and the previous (Flask-based) incarnation:

- Date/times in JSON responses are encoded in ISO-8601 format (old used RFC-1123 with a hardcoded
  'GMT' timezone). ISO-8601 is the default format used by Django in all JSON responses, and, since it
  is also actually compatible with JavaScript, we decided to keep it. We suggest using
  [dateutil](https://dateutil.readthedocs.io/en/stable/) in Python projects to parse the timestamp.
  As it auto-detects the format, it can be used to transparently switch between the old and this
  Blender ID.
- Anonymous requests to a protected endpoint return a `403 Forbidden` response (old used `401
  Unauthorized`). This is the default Django behaviour.


## Migrating database from old to this Blender ID

The old Blender ID database can be migrated to the current one. This does require you to run MySQL
as the database.

1. Make sure you have a fresh `blender_id_new` MySQL database.
2. Load a backup of the old database into the current database, like `bzcat
   blender-id-backup-2017-11-14-1107.sql.bz2 | mysql blender_id_new`.
3. Create the current database structure using `manage.py migrate`.
4. Migrate the old data to the new structure using `manage.py migrate_olddb`.
5. Make yourself a super-user with `manage.py makesuperuser your.email@example.com`
6. After testing that everything works, remove the old data using `manage.py drop_olddb`.

Users with an invalid email address (based on format and length) are skipped. Note that migrating of
user-roles and user-settings will cause warnings; some users are skipped

The following tables are explicitly *not* migrated:
- collections
- cloud_membership
- cloud_subscription
- gooseberry_pledge
- mail_queue
- mail_queue_prepaid
- mail_queue_recurring
- users_collections
