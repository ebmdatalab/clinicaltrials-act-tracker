# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0032_auto_20180521_1300'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE frontend_trial ALTER sponsor_id TYPE varchar(200);'),
    ]
