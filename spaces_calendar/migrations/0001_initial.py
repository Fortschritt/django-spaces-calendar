# -*- coding: utf-8 -*-
# Generated by Django 1.9b1 on 2015-11-10 12:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('spaces', '0003_auto_20151029_1353'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpacesCalendar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='spaces.Space')),
            ],
        ),
    ]
