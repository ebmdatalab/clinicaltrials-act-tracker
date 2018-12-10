# Generated by Django 2.0.3 on 2018-12-10 13:21

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0033_manual_pk_fix'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='trialqa',
            options={'ordering': ('submitted_to_regulator', 'id')},
        ),
        migrations.AddField(
            model_name='trialqa',
            name='first_seen_date',
            field=models.DateField(default=datetime.date.today, null=True),
        ),
        migrations.AlterField(
            model_name='trial',
            name='previous_status',
            field=models.CharField(blank=True, choices=[('overdue', 'Overdue'), ('overdue-cancelled', 'Overdue (cancelled results)'), ('ongoing', 'Ongoing'), ('reported', 'Reported'), ('reported-late', 'Reported (late)')], default='ongoing', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='trial',
            name='status',
            field=models.CharField(choices=[('overdue', 'Overdue'), ('overdue-cancelled', 'Overdue (cancelled results)'), ('ongoing', 'Ongoing'), ('reported', 'Reported'), ('reported-late', 'Reported (late)')], default='ongoing', max_length=20),
        ),
    ]