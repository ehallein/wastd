# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-08 09:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0021_merge_20180308_1153'),
    ]

    operations = [
        migrations.CreateModel(
            name='HbvParent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ogc_fid', models.BigIntegerField(blank=True, db_index=True, help_text='The OCG Feature ID of the record, used to identify the record in GeoServer.', null=True, unique=True, verbose_name='GeoServer OGC FeatureID')),
                ('name_id', models.BigIntegerField(blank=True, db_index=True, help_text='WACensus NameID, assigned by WACensus.', null=True, verbose_name='NameID')),
                ('class_id', models.CharField(blank=True, help_text='', max_length=100, null=True, verbose_name='WACensus ClassID')),
                ('parent_nid', models.BigIntegerField(blank=True, db_index=True, help_text='WACensus NameID, assigned by WACensus.', null=True, verbose_name='NameID')),
                ('updated_by', models.CharField(blank=True, help_text='The person or system who updated this record last in WACensus.', max_length=100, null=True, verbose_name='Updated by')),
                ('updated_on', models.CharField(blank=True, help_text='Date on which this record was updated in WACensus.', max_length=100, null=True, verbose_name='WACensus updated on')),
                ('md5_rowhash', models.CharField(blank=True, help_text='An MD5 hash of the record, used to indicate updates.', max_length=500, null=True, verbose_name='GeoServer MD5 rowhash')),
            ],
            options={
                'ordering': ['ogc_fid'],
                'verbose_name': 'HBV Parent',
                'verbose_name_plural': 'HBV Parents',
            },
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='class_name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Class'),
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='division_name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Division'),
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='family_name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Family Name'),
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='kingdom_name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Kingdom'),
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='order_name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Order Name'),
        ),
        migrations.AlterField(
            model_name='hbvfamily',
            name='supra_code',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='HBV Suprafamily Group Code'),
        ),
        migrations.AlterField(
            model_name='hbvgroup',
            name='class_id',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='HBV Suprafamily Group Code'),
        ),
        migrations.AlterField(
            model_name='hbvspecies',
            name='consv_code',
            field=models.CharField(blank=True, help_text='', max_length=100, null=True, verbose_name='Conservation Code'),
        ),
        migrations.AlterField(
            model_name='hbvspecies',
            name='naturalised',
            field=models.CharField(blank=True, help_text='', max_length=100, null=True, verbose_name='Naturalised'),
        ),
        migrations.AlterField(
            model_name='hbvspecies',
            name='ranking',
            field=models.CharField(blank=True, help_text='', max_length=100, null=True, verbose_name='Ranking'),
        ),
    ]
