# Generated by Django 2.2.1 on 2019-05-17 15:59

from django.db import migrations
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('bid_main', '0027_auto_after_django_upgrade_2_0_13'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=sorl.thumbnail.fields.ImageField(blank=True, null=True, upload_to='user-avatars'),
        ),
    ]
