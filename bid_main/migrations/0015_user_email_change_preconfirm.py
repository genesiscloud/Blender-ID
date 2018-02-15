# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-07 13:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bid_main', '0014_usernote'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_change_preconfirm',
            field=models.EmailField(blank=True, help_text='New address for the user, set while in the confirmation flow.', max_length=64, verbose_name='email address to change to'),
        ),
    ]