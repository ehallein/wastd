# Generated by Django 2.0.8 on 2019-01-23 02:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conservation', '0005_auto_20190122_1638'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementaction',
            name='document',
            field=models.ForeignKey(blank=True, help_text='The document in which this management action is specified.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='conservation.Document', verbose_name='Plan document'),
        ),
    ]
