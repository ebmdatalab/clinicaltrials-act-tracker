# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0032_auto_20180521_1300'),
    ]

    operations = [
        migrations.AlterField('trial', 'sponsor_id', models.CharField(max_length=200)),
    ]
