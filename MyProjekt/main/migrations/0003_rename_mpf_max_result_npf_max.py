# Generated by Django 3.2 on 2021-04-18 15:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_result'),
    ]

    operations = [
        migrations.RenameField(
            model_name='result',
            old_name='mpf_max',
            new_name='npf_max',
        ),
    ]
