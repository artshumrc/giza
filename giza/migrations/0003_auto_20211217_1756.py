# Generated by Django 3.2.9 on 2021-12-17 22:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('giza', '0002_auto_20211217_1719'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collection',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='lesson',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='topic',
            name='slug',
        ),
    ]