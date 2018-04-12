# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-11 05:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conservation', '0014_auto_20180411_1314'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communitygazettal',
            name='scope',
            field=models.PositiveIntegerField(choices=[(0, 'WA'), (1, 'CMW'), (2, 'INT')], default=0, help_text='In which legislation does this Gazettal apply?', verbose_name='Scope'),
        ),
        migrations.AlterField(
            model_name='taxongazettal',
            name='scope',
            field=models.PositiveIntegerField(choices=[(0, 'WA'), (1, 'CMW'), (2, 'INT')], default=0, help_text='In which legislation does this Gazettal apply?', verbose_name='Scope'),
        ),
    ]