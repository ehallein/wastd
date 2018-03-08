# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-01 04:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('observations', '0066_auto_20170131_1152'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tracktallyobservation',
            name='nest_type',
            field=models.CharField(choices=[('false-crawl', 'track without nest'), ('successful-crawl', 'track with nest'), ('track-unsure', 'track, checked for nest, unsure if nest'), ('track-not-assessed', 'track, not checked for nest'), ('nest', 'nest, unhatched, no track'), ('hatched-nest', 'nest, hatched'), ('body-pit', 'body pit, no track')], default='track-not-assessed', help_text='The track or nest type.', max_length=300, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='turtlenestencounter',
            name='nest_type',
            field=models.CharField(choices=[('false-crawl', 'track without nest'), ('successful-crawl', 'track with nest'), ('track-unsure', 'track, checked for nest, unsure if nest'), ('track-not-assessed', 'track, not checked for nest'), ('nest', 'nest, unhatched, no track'), ('hatched-nest', 'nest, hatched'), ('body-pit', 'body pit, no track')], default='track-not-assessed', help_text='The track or nest type.', max_length=300, verbose_name='Type'),
        ),
    ]
