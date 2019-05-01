# Generated by Django 2.1.7 on 2019-05-01 05:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0036_merge_20181211_1423'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ranking',
            name='percentage',
            field=models.DecimalField(decimal_places=2, max_digits=6, null=True),
        ),
        migrations.RunSQL(["UPDATE frontend_ranking SET percentage = NULL"]),
        migrations.RunSQL(["UPDATE frontend_ranking SET percentage = (reported * 100 / due) WHERE due IS NOT NULL"])
    ]