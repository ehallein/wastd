# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-19 08:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('observations', '0094_auto_20171115_1232'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='nest_age',
            field=models.CharField(choices=[('old', '(O) old, made before last night'), ('fresh', '(F) fresh, made last night'), ('unknown', '(U) unknown age'), ('missed', '(M) missed turtle, made within past hours')], default='unknown', help_text='The track or nest age.', max_length=300, verbose_name='Age'),
        ),
        migrations.AlterField(
            model_name='turtlenestencounter',
            name='nest_age',
            field=models.CharField(choices=[('old', '(O) old, made before last night'), ('fresh', '(F) fresh, made last night'), ('unknown', '(U) unknown age'), ('missed', '(M) missed turtle, made within past hours')], default='unknown', help_text='The track or nest age.', max_length=300, verbose_name='Age'),
        ),
    ]