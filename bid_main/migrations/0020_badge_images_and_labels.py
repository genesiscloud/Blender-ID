# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-11 15:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bid_main', '0019_user_privacy_policy_agreed'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='badge_img',
            field=models.ImageField(blank=True, height_field='badge_img_height', help_text='Visual representation of a badge.', null=True, upload_to='badges', width_field='badge_img_width'),
        ),
        migrations.AddField(
            model_name='role',
            name='badge_img_height',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='role',
            name='badge_img_width',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='role',
            name='label',
            field=models.CharField(blank=True, help_text='Human-readable name for a badge. Required for badges, not for roles.', max_length=255),
        ),
        migrations.AddField(
            model_name='role',
            name='link',
            field=models.URLField(blank=True, help_text='Clicking on a badge image will lead to this link.', null=True),
        ),
        migrations.AlterField(
            model_name='role',
            name='is_public',
            field=models.BooleanField(default=True, help_text='When enabled, this role/badge will be readable through the userinfo API.'),
        ),
        migrations.AlterField(
            model_name='role',
            name='description',
            field=models.CharField(blank=True, help_text="Note that this is shown for badges on users' dashboard page.", max_length=255),
        ),
    ]