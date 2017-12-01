# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-01 11:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('enabled', models.BooleanField(default=True)),
                ('hook_type', models.CharField(choices=[('USER_MODIFIED', 'User Modified')], db_index=True, default='USER_MODIFIED', max_length=32)),
                ('url', models.URLField()),
                ('secret', models.CharField(max_length=64)),
                ('description', models.TextField(blank=True, help_text='Description of this webhook, for staff-eyes only.')),
            ],
        ),
    ]
