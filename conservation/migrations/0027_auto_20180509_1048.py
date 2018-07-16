# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-05-09 02:48
from __future__ import unicode_literals

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('conservation', '0026_document_last_reviewed_on'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communitygazettal',
            name='status',
            field=django_fsm.FSMIntegerField(choices=[(0, 'Proposed'), (10, 'In review with experts'), (20, 'In review with public'), (30, 'In review with panel'), (40, 'In review with Branch Manager'), (50, 'In review with Division Director'), (60, 'In review with Director General'), (70, 'In review with Minister'), (80, 'Listed'), (90, 'De-listed'), (100, 'Rejected')], db_index=True, default=0, help_text='The approval status of the Conservation Listing.', verbose_name='Approval status'),
        ),
        migrations.AlterField(
            model_name='taxongazettal',
            name='status',
            field=django_fsm.FSMIntegerField(choices=[(0, 'Proposed'), (10, 'In review with experts'), (20, 'In review with public'), (30, 'In review with panel'), (40, 'In review with Branch Manager'), (50, 'In review with Division Director'), (60, 'In review with Director General'), (70, 'In review with Minister'), (80, 'Listed'), (90, 'De-listed'), (100, 'Rejected')], db_index=True, default=0, help_text='The approval status of the Conservation Listing.', verbose_name='Approval status'),
        ),
    ]