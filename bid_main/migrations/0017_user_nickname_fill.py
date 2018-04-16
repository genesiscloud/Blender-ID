"""Give everybody with a NULL nickname something based on their full name."""
from __future__ import unicode_literals

from django.db import migrations, IntegrityError, transaction


def set_nickname(model, user, nickname) -> bool:
    """Set the nickname, return True iff saving was successful."""

    count = model.objects.filter(nickname=nickname).count()
    if count > 0:
        print(f'already {count} user(s) with nickname {nickname!r}')
        return False

    user.nickname = nickname
    user.save(update_fields=['nickname'])
    return True


def random_nums():
    """Increasingly larger random number generator."""
    import random

    lower, upper = 1, 5
    while True:
        yield random.randint(lower, upper-1)
        lower, upper = upper, upper * 3


def fill_nicknames(apps, schema_editor):
    """Give users with a NULL nickname something based on their full name."""
    import re
    import datetime

    # We can't import the User model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    User = apps.get_model('bid_main', 'User')

    illegal = re.compile(r'[^\w.+-]')
    strip_email = re.compile('@.*$')

    users = User.objects.filter(nickname=None)
    total_users = users.count()
    last_report = 0
    start = datetime.datetime.now()
    print()
    print(f'    - migrating {total_users} users.')
    for idx, user in enumerate(users):
        perc = idx / total_users
        if perc - last_report > 0.10:
            last_report = perc
            print(f'    - {idx} ({int(perc*100)}%)')

        # We cannot migrate the entire database in one transaction (too many
        # queries for MySQL to handle), so do one transaction per user.
        base = user.full_name or strip_email.sub('', user.email)
        base = illegal.sub('', base)[:50]
        if set_nickname(User, user, base):
            continue

        # Try increasingly larger random numbers as a suffix.
        for num in random_nums():
            if set_nickname(User, user, f'{base}-{num}'):
                break

    end = datetime.datetime.now()  # assume the timezone hasn't changed.
    print(f'Migration of {total_users} took {end - start}')


def fake_reverse(apps, schema_editor):
    """Allow reversal of this migration really reversing."""

    # We can't import the User model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    User = apps.get_model('bid_main', 'User')
    for user in User.objects.filter(nickname__isnull=False):
        user.nickname = None
        user.save()


class Migration(migrations.Migration):
    dependencies = [
        ('bid_main', '0016_user_nickname'),
    ]

    operations = [
        migrations.RunPython(fill_nicknames, fake_reverse),
    ]
