# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-19 08:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('observations', '0089_auto_20170324_1133'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tagobservation',
            name='tag_type',
            field=models.CharField(choices=[('flipper-tag', 'Flipper Tag'), ('pit-tag', 'PIT Tag'), ('sat-tag', 'Satellite Relay Data Logger'), ('blood-sample', 'Blood Sample'), ('biopsy-sample', 'Biopsy Sample'), ('stomach-content-sample', 'Stomach Content Sample'), ('physical-sample', 'Physical Sample'), ('egg-sample', 'Egg Sample'), ('qld-monel-a-flipper-tag', 'QLD Monel Series A flipper tag'), ('qld-titanium-k-flipper-tag', 'QLD Titanium Series K flipper tag'), ('qld-titanium-t-flipper-tag', 'QLD Titanium Series T flipper tag'), ('acoustic-tag', 'Acoustic tag'), ('commonwealth-titanium-flipper-tag', 'Commonwealth titanium flipper tag'), ('cayman-juvenile-tag', 'Cayman juvenile tag'), ('hawaii-inconel-flipper-tag', 'Hawaii Inst Mar Biol Inconel tag'), ('ptt', 'Platform Transmitter Terminal (PTT)'), ('rototag', 'RotoTag'), ('narangebub-nickname', 'Narangebup rehab informal name'), ('aqwa-nickname', 'AQWA informal name'), ('atlantis-nickname', 'Atlantis informal name'), ('wa-museum-reptile-registration-number', 'WA Museum Natural History Reptiles Catalogue Registration Number'), ('genetic-tag', 'Genetic ID sequence'), ('other', 'Other')], default='flipper-tag', help_text='What kind of tag is it?', max_length=300, verbose_name='Tag type'),
        ),
    ]
