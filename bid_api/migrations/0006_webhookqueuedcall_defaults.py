# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-13 08:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bid_api', '0005_webhook_last_flush_attempt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='webhookqueuedcall',
            name='error_code',
            field=models.IntegerField(blank=True, default=0, help_text='The HTTP status code received when POSTing'),
        ),
        migrations.AlterField(
            model_name='webhookqueuedcall',
            name='error_msg',
            field=models.TextField(blank=True, default='', help_text='The HTTP response received when POSTing'),
        ),
    ]