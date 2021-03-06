# Generated by Django 2.2.7 on 2019-11-05 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bid_main', '0029_user_avatar_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='deletion_requested',
            field=models.BooleanField(default=False, help_text='Indicates whether deletion of this account was requested. Once turned on, should not be turned off.'),
        ),
    ]
