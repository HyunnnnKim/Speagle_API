# Generated by Django 3.0 on 2019-12-09 13:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='hash_id',
        ),
    ]
