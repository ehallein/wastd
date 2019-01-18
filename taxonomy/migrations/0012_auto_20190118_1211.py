# Generated by Django 2.0.8 on 2019-01-18 04:11

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0011_auto_20181204_1908'),
    ]

    operations = [
        migrations.AlterField(
            model_name='community',
            name='source_id',
            field=models.CharField(default=uuid.UUID('1cb34a0e-1ad7-11e9-a86f-ecf4bb19b5fc'), help_text='The ID of the record in the original source, if available.', max_length=1000, verbose_name='Source ID'),
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
            model_name='hbvparent',
            name='class_id',
            field=models.CharField(blank=True, help_text='', max_length=100, null=True, verbose_name='WACensus ClassID'),
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
        migrations.AlterField(
            model_name='hbvvernacular',
            name='name',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='hbvvernacular',
            name='vernacular',
            field=models.CharField(blank=True, help_text='', max_length=1000, null=True, verbose_name='Vernacular Name'),
        ),
    ]
