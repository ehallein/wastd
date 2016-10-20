# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-13 03:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('observations', '0034_auto_20161013_1132'),
    ]

    operations = [
        migrations.AddField(
            model_name='temperatureloggersettings',
            name='logging_interval',
            field=models.DurationField(blank=True, help_text='The time between individual readings. Format: 1d 23:59:59. E.g, 1h is 01:00:00', null=True, verbose_name='Logging interval'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='bird_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Bird predation'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='croc_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Crocodile predation'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='dingo_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Dingo predation'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='dog_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Dog predation'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='fox_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Fox predation'),
        ),
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='goanna_predation',
            field=models.CharField(choices=[('na', 'NA'), ('absent', 'Confirmed absent'), ('present', 'Confirmed present')], default='na', help_text='', max_length=300, verbose_name='Goanna predation'),
        ),
    ]